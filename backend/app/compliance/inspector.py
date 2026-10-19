"""The Inspector: pasted text in, verified facts and a report out (Technical Design §4, steps 1–8).

The LLM supplies facts and labels; code verifies them and the rule engine decides every verdict.
"""

import hashlib
from dataclasses import dataclass
from datetime import date

from app.compliance.classification import Classification, classify, safety_net
from app.compliance.engine import evaluate
from app.compliance.extraction import PROMPTS_DIR, Extraction, Verified, extract, verify
from app.compliance.llm import ModelSettings, StructuredLLM
from app.compliance.models import AIDisclosure, Context, Facts, Report, Requirement, VacancyStatement
from app.compliance.money import parse_pay
from app.compliance.normalise import NormalisedText, normalise
from app.compliance.rulepack import RulePack

REFUSALS = {
    "empty": "Paste a job posting to check it.",
    "not_a_posting": "This doesn't look like a job posting. Paste one job posting to check it.",
    "multiple_postings": "This looks like more than one job posting. Paste one posting at a time.",
    "french": "French and bilingual postings aren't supported yet. French support is coming.",
}


class InputRefused(Exception):
    """The input can't be checked in v1. No verdicts, and the free check should not use up a credit."""

    def __init__(self, reason: str) -> None:
        super().__init__(REFUSALS[reason])
        self.reason = reason
        self.message = REFUSALS[reason]


@dataclass(frozen=True)
class Inspection:
    document: NormalisedText
    facts: Facts
    report: Report


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def prompt_version() -> str:
    return _hash("".join((PROMPTS_DIR / name).read_text(encoding="utf-8") for name in ("extract.md", "classify.md")))


def _check_input(extraction: Extraction) -> None:
    if extraction.input_kind != "one_posting":
        raise InputRefused(extraction.input_kind)
    if extraction.contains_french:
        raise InputRefused("french")


def _vacancy(doc: NormalisedText, labels: list) -> VacancyStatement:
    spans = {s.id: s.span for s in doc.sentences}
    definite = [label for label in labels if label.label in ("existing", "not_existing")]
    if definite and len({label.label for label in definite}) == 1:
        return VacancyStatement(present=True, polarity=definite[0].label, span=spans[definite[0].sentence])
    unclear = definite or [label for label in labels if label.label == "vague"]
    if unclear:  # conflicting or vague statements
        return VacancyStatement(present=True, polarity="vague", span=spans[unclear[0].sentence])
    return VacancyStatement()


def _ai(doc: NormalisedText, labels: list) -> AIDisclosure:
    spans = {s.id: s.span for s in doc.sentences}
    for polarity in ("uses_ai", "no_ai"):
        if found := [label for label in labels if label.label == polarity]:
            return AIDisclosure(present=True, polarity=polarity, span=spans[found[0].sentence])
    return AIDisclosure()


def _facts(
    doc: NormalisedText, verified: Verified, labels: Classification, wanted: dict[str, list[int]]
) -> Facts:
    sentences = {s.id: s for s in doc.sentences}

    def requested(task: str) -> list:
        first: dict[int, object] = {}
        for label in getattr(labels, task):
            if label.sentence in wanted[task]:
                first.setdefault(label.sentence, label)
        return [first[i] for i in wanted[task] if i in first]

    requirements = [
        Requirement(
            text=sentences[label.sentence].text,
            span=sentences[label.sentence].span,
            cex_label=label.label,
            reason=label.reason,
        )
        for label in requested("canadian_experience")
    ]
    extraction = verified.extraction
    return Facts(
        title=verified.title,
        locations=verified.locations,
        pay=verified.pay,
        vacancy_statement=_vacancy(doc, requested("vacancy")),
        ai_disclosure=_ai(doc, requested("ai")),
        requirements=requirements,
        specific_position=extraction.specific_position,
        internal_only=extraction.internal_only,
        work_in_ontario=extraction.work_in_ontario,
    )


def inspect(
    text: str,
    ctx: Context,
    posting_date: date,
    pack: RulePack,
    llm: StructuredLLM,
    settings: ModelSettings = ModelSettings(),
) -> Inspection:
    doc = normalise(text)
    if not doc.sentences:
        raise InputRefused("empty")
    readings = parse_pay(doc.text)

    extraction = extract(doc, llm, settings)
    _check_input(extraction)
    verified = verify(doc, extraction, readings)
    if verified.problems:  # one retry with the problems as feedback; what still fails is dropped or flagged
        extraction = extract(doc, llm, settings, feedback=verified.problems)
        _check_input(extraction)
        verified = verify(doc, extraction, readings)

    wanted = {
        "canadian_experience": sorted(set(verified.requirement_ids) | safety_net(doc)),
        "vacancy": verified.vacancy_ids,
        "ai": verified.ai_ids,
    }
    labels = classify(doc, wanted, pack, llm, settings)
    facts = _facts(doc, verified, labels, wanted)

    report = evaluate(facts, ctx, pack, posting_date)
    versions = {
        **report.versions,
        "model": settings.model,
        "prompts": prompt_version(),
        "profile_hash": _hash(ctx.model_dump_json()),
        "text_hash": _hash(doc.text),
    }
    return Inspection(document=doc, facts=facts, report=report.model_copy(update={"versions": versions}))
