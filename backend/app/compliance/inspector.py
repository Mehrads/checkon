"""The Inspector: pasted text in, verified facts and a report out (Technical Design §4, steps 1–8).

The LLM supplies facts and labels; code verifies them and the rule engine decides every verdict.
"""

import hashlib
from dataclasses import dataclass
from datetime import date

from app.compliance.classification import Classification, classify, safety_net
from app.compliance.engine import evaluate
from app.compliance.extraction import PROMPTS_DIR, Extraction, extract, verify
from app.compliance.llm import ModelSettings, StructuredLLM
from app.compliance.models import (
    AIDisclosure,
    Context,
    Facts,
    PayMention,
    Report,
    Requirement,
    TextFact,
    VacancyStatement,
)
from app.compliance.money import parse_pay
from app.compliance.normalise import NormalisedText, normalise
from app.compliance.rulepack import RulePack
from app.compliance.wording import load_wording

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
class SentenceLabels:
    cex: str | None = None
    cex_reason: str | None = None
    vacancy: str | None = None
    ai: str | None = None


@dataclass(frozen=True)
class Inspection:
    document: NormalisedText
    extraction: Extraction
    labels: dict[int, SentenceLabels]  # by sentence id; sentences with no labels are absent
    facts: Facts
    report: Report


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def prompt_version() -> str:
    names = ("extract.md", "classify.md", "rewrite.md")
    return content_hash("".join((PROMPTS_DIR / name).read_text(encoding="utf-8") for name in names))


def _check_input(extraction: Extraction) -> None:
    if extraction.input_kind != "one_posting":
        raise InputRefused(extraction.input_kind)
    if extraction.contains_french:
        raise InputRefused("french")


def labels_by_sentence(result: Classification, wanted: dict[str, list[int]]) -> dict[int, SentenceLabels]:
    """First label per wanted sentence and task; labels for sentences nobody asked about are ignored."""
    found: dict[int, dict[str, str]] = {}
    for task, key in (("canadian_experience", "cex"), ("vacancy", "vacancy"), ("ai", "ai")):
        for label in getattr(result, task):
            if label.sentence in wanted[task]:
                entry = found.setdefault(label.sentence, {})
                if key not in entry:
                    entry[key] = label.label
                    if key == "cex":
                        entry["cex_reason"] = label.reason
    return {sentence: SentenceLabels(**entry) for sentence, entry in found.items()}


def _vacancy(doc: NormalisedText, labels: dict[int, SentenceLabels]) -> VacancyStatement:
    spans = {s.id: s.span for s in doc.sentences}
    found = [(i, labels[i].vacancy) for i in sorted(labels) if labels[i].vacancy not in (None, "none")]
    definite = [(i, label) for i, label in found if label in ("existing", "not_existing")]
    if definite and len({label for _, label in definite}) == 1:
        return VacancyStatement(present=True, polarity=definite[0][1], span=spans[definite[0][0]])
    if found:  # conflicting or vague statements
        return VacancyStatement(present=True, polarity="vague", span=spans[(definite or found)[0][0]])
    return VacancyStatement()


def _ai(doc: NormalisedText, labels: dict[int, SentenceLabels]) -> AIDisclosure:
    spans = {s.id: s.span for s in doc.sentences}
    for polarity in ("uses_ai", "no_ai"):
        if found := [i for i in sorted(labels) if labels[i].ai == polarity]:
            return AIDisclosure(present=True, polarity=polarity, span=spans[found[0]])
    return AIDisclosure()


def build_facts(
    doc: NormalisedText,
    extraction: Extraction,
    labels: dict[int, SentenceLabels],
    pay: list[PayMention],
    title: TextFact | None,
    locations: list[TextFact],
    placeholder: str,
) -> Facts:
    requirements = [
        Requirement(text=s.text, span=s.span, cex_label=labels[s.id].cex, reason=labels[s.id].cex_reason)
        for s in doc.sentences
        if s.id in labels and labels[s.id].cex
    ]
    start = doc.text.find(placeholder)
    return Facts(
        title=title,
        locations=locations,
        pay=pay,
        vacancy_statement=_vacancy(doc, labels),
        ai_disclosure=_ai(doc, labels),
        requirements=requirements,
        specific_position=extraction.specific_position,
        internal_only=extraction.internal_only,
        work_in_ontario=extraction.work_in_ontario,
        pay_placeholder=(start, start + len(placeholder)) if start >= 0 else None,
    )


def versioned(report: Report, ctx: Context, doc: NormalisedText, settings: ModelSettings) -> Report:
    versions = {
        **report.versions,
        "model": settings.model,
        "prompts": prompt_version(),
        "profile_hash": content_hash(ctx.model_dump_json()),
        "text_hash": content_hash(doc.text),
    }
    return report.model_copy(update={"versions": versions})


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
    labels = labels_by_sentence(classify(doc, wanted, pack, llm, settings), wanted)
    placeholder = load_wording(pack.jurisdiction).placeholder
    facts = build_facts(doc, extraction, labels, verified.pay, verified.title, verified.locations, placeholder)
    report = versioned(evaluate(facts, ctx, pack, posting_date), ctx, doc, settings)
    return Inspection(document=doc, extraction=extraction, labels=labels, facts=facts, report=report)
