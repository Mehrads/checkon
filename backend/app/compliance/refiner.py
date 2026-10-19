"""The Refiner: verified patches for failing findings (Technical Design §5).

Each patch fixes one finding and touches one span. Code, the template or the wording library writes
every patch except Canadian-experience rewrites, which an LLM writes for that one sentence only.
All patches are applied together and re-inspected; a patch that fails an acceptance test is retried
once if an LLM wrote it, and otherwise dropped with the rule's manual guidance.
"""

import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_FLOOR, Decimal
from itertools import count
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.compliance.checks import annualise
from app.compliance.classification import classify, rule_block, safety_net
from app.compliance.engine import evaluate
from app.compliance.extraction import PROMPTS_DIR
from app.compliance.inspector import Inspection, SentenceLabels, build_facts, labels_by_sentence, versioned
from app.compliance.llm import REWRITE_SETTINGS, LLMError, ModelSettings, StructuredLLM
from app.compliance.models import (
    Context,
    PayKind,
    PayMention,
    PayUnit,
    Question,
    Report,
    RuleResult,
    Span,
    Verdict,
)
from app.compliance.money import parse_pay, restate_range
from app.compliance.normalise import NormalisedText, fold, normalise
from app.compliance.rulepack import RulePack
from app.compliance.wording import Variant, WordingLibrary, load_wording

Writer = Literal["template", "code", "wording_library", "llm"]
_PAY_HEADING = re.compile(r"compensation|salary|pay|wage|benefit", re.IGNORECASE)
_STEP = {PayUnit.HOUR: Decimal("0.25"), PayUnit.WEEK: Decimal(10), PayUnit.MONTH: Decimal(100), PayUnit.YEAR: Decimal(1000)}
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
_NAME = re.compile(r"\b[A-Z][\w.&'-]*")
_FIXED = (Verdict.PASS, Verdict.NOT_APPLICABLE)


class Patch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    rule: str
    op: Literal["replace", "insert", "delete"]
    span: Span  # in the inspected (normalised) text; (p, p) for an insert
    original_span: Span = (0, 0)  # the same place in the pasted text
    before: str
    after: str | None  # None until the employer picks one of `options`
    options: list[str] = []
    writer: Writer
    default: bool = True  # applied unless the user rejects it; suggestions are False
    verified: bool = False


class Dropped(BaseModel):
    rule: str
    span: Span | None
    guidance: str
    failures: list[str] = []


class Refinement(BaseModel):
    patches: list[Patch]
    questions: list[Question]
    dropped: list[Dropped]
    text: str  # the pasted posting with every default patch applied
    report: Report  # verdicts on that text


class _Rewrite(BaseModel):
    sentence: str


# Planning


@dataclass
class _Plan:
    patches: list[Patch] = field(default_factory=list)
    questions: list[Question] = field(default_factory=list)
    dropped: list[Dropped] = field(default_factory=list)


def _line(text: str, pos: int) -> tuple[int, int]:
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    return start, len(text) if end < 0 else end


def _tidy(text: str) -> bool:
    return "\n\n\n" not in text and text == text.strip() and "  " not in text


def _deletion(text: str, sentence: Span) -> Span:
    """The span that removes a sentence: its line if the line holds nothing else, without leaving a gap."""
    line_start, line_end = _line(text, sentence[0])
    content = text[line_start:line_end]
    if content.strip(" -*•·▪◦‣○●■□➢➤✓✔") != text[sentence[0] : sentence[1]]:
        end = sentence[1] + (1 if text[sentence[1] : sentence[1] + 1] == " " else 0)
        return (sentence[0], end)
    candidates = [(line_start, line_end + 1), (line_start, line_end + 2), (line_start - 1, line_end), (line_start - 2, line_end)]
    for start, end in candidates:
        if 0 <= start <= end <= len(text) and _tidy(text[:start] + text[end:]):
            return (start, end)
    return (line_start, min(line_end + 1, len(text)))


def _pay_point(doc: NormalisedText) -> tuple[int, str]:
    """End of the first paragraph under a pay heading, else the end of the posting."""
    text = doc.text
    for section in doc.sections:
        if section.heading and _PAY_HEADING.search(section.heading.value):
            pos = section.heading.span[1]
            while pos < len(text):
                line_start = pos + 1
                line_end = text.find("\n", line_start)
                line_end = len(text) if line_end < 0 else line_end
                if line_start >= len(text) or line_start == line_end:  # a blank line ends the paragraph
                    break
                pos = line_end
            return pos, "\n"
    return len(text), "\n\n"


def _floor(value: Decimal, step: Decimal) -> Decimal:
    return (value / step).to_integral_value(ROUND_FLOOR) * step


def range_options(pay: PayMention, ctx: Context, params: dict) -> list[tuple[Decimal, Decimal]]:
    """Ranges within the cap, in the posting's own unit: keep the bottom, centre, keep the top."""
    hours = ctx.hours_per_week if ctx.hours_per_week is not None else params["default_hours_per_week"]
    per_unit = annualise(Decimal(1), pay.unit, hours, params)
    step = _STEP[pay.unit]
    width = _floor(params["max_annual_width"] / per_unit, step)
    low = _floor((pay.min + pay.max) / 2 - width / 2, step)
    options = [(pay.min, pay.min + width), (low, low + width), (pay.max - width, pay.max)]
    return [option for option in dict.fromkeys(options) if option[0] >= 0]


def _plan(
    base: Inspection, ctx: Context, pack: RulePack, wording: WordingLibrary, variant: Variant
) -> _Plan:
    doc, facts = base.document, base.facts
    results = {r.rule: r for r in base.report.results}
    rules = {r.id: r for r in pack.rules}
    plan = _Plan()
    ids = count(1)
    end = len(doc.text)

    def patch(rule: str, op: str, span: Span, after: str | None, writer: Writer, **extra) -> None:
        plan.patches.append(
            Patch(id=f"p{next(ids)}", rule=rule, op=op, span=span, before=doc.text[span[0] : span[1]],
                  after=after, writer=writer, **extra)  # fmt: skip
        )

    def guidance(result: RuleResult, span: Span | None, reason: str) -> None:
        text = (result.fix or {}).get("guidance", result.message)
        plan.dropped.append(Dropped(rule=result.rule, span=span, guidance=text, failures=[reason]))

    def failing(rule: str, *verdicts: Verdict) -> RuleResult | None:
        result = results.get(rule)
        return result if result and result.verdict in (verdicts or (Verdict.FAIL,)) else None

    if failing("ON-PAY-01"):
        point, prefix = _pay_point(doc)
        patch("ON-PAY-01", "insert", (point, point), prefix + wording.placeholder, "template")

    if result := failing("ON-PAY-02"):
        for pay in facts.pay:
            if pay.span not in result.evidence:
                continue
            if pay.min is None or pay.max is None:
                guidance(result, pay.span, "An open-ended range needs the employer's own top or bottom figure.")
                continue
            text = doc.text[pay.span[0] : pay.span[1]]
            options = [restate_range(text, low, high) for low, high in range_options(pay, ctx, rules["ON-PAY-02"].params)]
            if options := [option for option in options if option]:
                patch("ON-PAY-02", "replace", pay.span, None, "code", options=options, default=False)
            else:
                guidance(result, pay.span, "No narrower range could be written in the posting's own format.")

    if result := failing("ON-VAC-01", Verdict.FAIL, Verdict.WARNING):
        if ctx.existing_vacancy is None:
            text = rules["ON-VAC-01"].questions["existing_vacancy"]
            plan.questions.append(Question(id="existing_vacancy", text=text))
        else:
            key = "vacancy_existing" if ctx.existing_vacancy else "vacancy_not_existing"
            patch("ON-VAC-01", "insert", (end, end), "\n\n" + wording.text(key, variant), "wording_library")

    if failing("ON-AI-01", Verdict.FAIL):
        disclosure = wording.text("ai_disclosure", variant)
        if facts.ai_disclosure.present and facts.ai_disclosure.polarity == "no_ai" and facts.ai_disclosure.span:
            patch("ON-AI-01", "replace", facts.ai_disclosure.span, disclosure, "wording_library")
        else:
            patch("ON-AI-01", "insert", (end, end), "\n\n" + disclosure, "wording_library")
    elif failing("ON-AI-01", Verdict.WARNING):  # says AI, employer says no: propose removing it
        for sentence in doc.sentences:
            if base.labels.get(sentence.id, SentenceLabels()).ai == "uses_ai":
                patch("ON-AI-01", "delete", _deletion(doc.text, sentence.span), "", "code")

    if failing("ON-CEX-01", Verdict.FAIL, Verdict.WARNING):
        for requirement in facts.requirements:
            if requirement.cex_label in ("violation", "borderline"):
                patch("ON-CEX-01", "replace", requirement.span, None, "llm",
                      default=requirement.cex_label == "violation")  # fmt: skip
    return plan


# Applying patches and re-inspecting what changed


@dataclass
class _Applied:
    text: str
    spans: dict[str, Span]  # patch id -> where its text landed
    start: Callable[[int], int]
    end: Callable[[int], int]
    touched: Callable[[Span], bool]


def apply_edits(text: str, patches: list[Patch]) -> _Applied:
    order = sorted(patches, key=lambda p: (p.span[0], p.span[1]))
    pieces, spans, cursor, length = [], {}, 0, 0
    for p in order:
        start, end = p.span
        if start < cursor:
            raise ValueError(f"patch {p.id} overlaps another patch")
        pieces.append(text[cursor:start])
        length += start - cursor
        spans[p.id] = (length, length + len(p.after or ""))
        pieces.append(p.after or "")
        length += len(p.after or "")
        cursor = end
    pieces.append(text[cursor:])
    edits = [(p.span[0], p.span[1], len(p.after or "") - (p.span[1] - p.span[0])) for p in order]

    def start_of(pos: int) -> int:
        return pos + sum(delta for s, e, delta in edits if e <= pos)

    def end_of(pos: int) -> int:
        return pos + sum(delta for s, e, delta in edits if e < pos or (e == pos and s < e))

    def touched(span: Span) -> bool:
        return any(s < e and s < span[1] and span[0] < e for s, e, _ in edits)

    return _Applied("".join(pieces), spans, start_of, end_of, touched)


class _Unstable(Exception):
    pass


@dataclass
class _Context:
    base: Inspection
    ctx: Context
    posting_date: date
    pack: RulePack
    wording: WordingLibrary
    llm: StructuredLLM
    classify_settings: ModelSettings
    rewrite_settings: ModelSettings
    label_cache: dict[str, SentenceLabels] = field(default_factory=dict)
    rewrites: dict[str, str] = field(default_factory=dict)  # sentence -> verified rewrite


def reinspect(c: _Context, patches: list[Patch]) -> tuple[Inspection, _Applied]:
    """Re-check the patched text: unchanged sentences keep their facts, changed ones are read again."""
    base = c.base
    applied = apply_edits(base.document.text, patches)
    doc = normalise(applied.text)
    if doc.text != applied.text:
        raise _Unstable("the patched text changes when normalised")

    def moved(span: Span) -> Span:
        return (applied.start(span[0]), applied.end(span[1]))

    old_at = {moved(s.span): s for s in base.document.sentences if not applied.touched(s.span)}
    labels: dict[int, SentenceLabels] = {}
    unread: list[int] = []
    for sentence in doc.sentences:
        if (old := old_at.get(sentence.span)) is not None:
            if old.id in base.labels:
                labels[sentence.id] = base.labels[old.id]
            continue
        if (declared := c.wording.labels_for(sentence.text)) is not None:
            if declared:
                labels[sentence.id] = SentenceLabels(**declared)
            continue
        source = next((p for p in patches if _overlaps(applied.spans[p.id], sentence.span)), None)
        if source is not None and source.writer != "llm":  # code kept the sentence's meaning: keep its labels
            old = next((s for s in base.document.sentences if _overlaps(s.span, source.span)), None)
            if old is not None and old.id in base.labels:
                labels[sentence.id] = base.labels[old.id]
            continue
        if sentence.text in c.label_cache:
            labels[sentence.id] = c.label_cache[sentence.text]
        elif source is not None or sentence.id in safety_net(doc):
            unread.append(sentence.id)
    if unread:
        wanted = {"canadian_experience": unread, "vacancy": [], "ai": []}
        fresh = labels_by_sentence(classify(doc, wanted, c.pack, c.llm, c.classify_settings), wanted)
        for sentence_id in unread:
            found = fresh.get(sentence_id, SentenceLabels())
            labels[sentence_id] = c.label_cache[doc.sentences[sentence_id].text] = found

    pay = [m.model_copy(update={"span": moved(m.span)}) for m in base.facts.pay if not applied.touched(m.span)]
    for p in patches:
        if p.rule == "ON-PAY-02" and p.op == "replace":
            start, end = applied.spans[p.id]
            for reading in parse_pay(doc.text[start:end])[:1]:
                old_unit = next((m.unit for m in base.facts.pay if m.span == p.span), PayUnit.YEAR)
                pay.append(
                    PayMention(min=reading.min, max=reading.max, unit=reading.unit or old_unit, kind=PayKind.WAGE,
                               span=(start + reading.span[0], start + reading.span[1]))  # fmt: skip
                )
    pay.sort(key=lambda m: m.span)
    title = base.facts.title
    if title is not None:
        title = None if applied.touched(title.span) else title.model_copy(update={"span": moved(title.span)})
    locations = [
        loc.model_copy(update={"span": moved(loc.span)}) for loc in base.facts.locations if not applied.touched(loc.span)
    ]
    facts = build_facts(doc, base.extraction, labels, pay, title, locations, c.wording.placeholder)
    report = versioned(evaluate(facts, c.ctx, c.pack, c.posting_date), c.ctx, doc, c.classify_settings)
    inspection = Inspection(
        document=doc, context=c.ctx, extraction=base.extraction, labels=labels, facts=facts, report=report
    )
    return inspection, applied


def _overlaps(a: Span, b: Span) -> bool:
    return a[0] < b[1] and b[0] < a[1] or (a[0] == a[1] and b[0] <= a[0] < b[1])


# Acceptance tests (Technical Design §5)


def _outside(text: str, spans: list[Span]) -> list[str]:
    pieces, cursor = [], 0
    for start, end in sorted(spans):
        pieces.append(text[cursor:start])
        cursor = end
    pieces.append(text[cursor:])
    return pieces


def acceptance(c: _Context, patches: list[Patch], after: Inspection, applied: _Applied) -> dict[str, list[str]]:
    base = c.base
    text = base.document.text
    failures: dict[str, list[str]] = defaultdict(list)
    before_results = {r.rule: r for r in base.report.results}
    after_results = {r.rule: r for r in after.report.results}

    def blame(rule: str, message: str, candidates: list[Patch]) -> None:
        evidence = after_results[rule].evidence
        culprits = [p for p in candidates if any(_overlaps(applied.spans[p.id], e) for e in evidence)]
        for p in culprits or candidates:
            failures[p.id].append(message)

    # 1. Every patched rule now passes, or is needs_input behind the pay placeholder.
    patched = {p.rule for p in patches}
    for rule in patched:
        result = after_results[rule]
        placeholder = rule == "ON-PAY-01" and result.verdict == Verdict.NEEDS_INPUT and after.facts.pay_placeholder
        if result.verdict not in _FIXED and not placeholder:
            blame(rule, f"Test 1: {rule} is still {result.verdict.value}: {result.message}", [p for p in patches if p.rule == rule])

    # 2. No rule that passed now fails or warns.
    for rule, before in before_results.items():
        now = after_results[rule].verdict
        if rule not in patched and before.verdict not in (Verdict.FAIL, Verdict.WARNING) and now in (Verdict.FAIL, Verdict.WARNING):
            blame(rule, f"Test 2: {rule} was {before.verdict.value} and is now {now.value}.", patches)

    # 3. Nothing changed outside the patched spans.
    outside_before = _outside(text, [p.span for p in patches])
    outside_after = _outside(applied.text, [applied.spans[p.id] for p in patches])
    if outside_before != outside_after:
        for p in patches:
            failures[p.id].append("Test 3: text outside the patches changed.")

    sentences = base.document.sentences
    allowed_numbers = set(_NUMBER.findall(text))
    for entry in c.wording.entries.values():
        for variant in entry.variants.values():
            allowed_numbers.update(_NUMBER.findall(variant))
    for p in patches:
        new = p.after or ""
        # 4. No new facts: numbers and names come from the source sentence (LLM) or the posting.
        if p.writer == "llm":
            source = p.before
            names = _NAME.findall(new)[1:] if new[:1].isupper() else _NAME.findall(new)
            new_numbers = [n for n in _NUMBER.findall(new) if n not in _NUMBER.findall(source)]
            new_names = [n for n in names if n not in source]
            if new_numbers or new_names:
                failures[p.id].append(f"Test 4: new facts not in the original sentence: {', '.join(new_numbers + new_names)}.")
        elif p.writer in ("template", "wording_library"):
            if extra := [n for n in _NUMBER.findall(new) if n not in allowed_numbers]:
                failures[p.id].append(f"Test 4: new numbers: {', '.join(extra)}.")
        # 5. Each patch stays inside its own sentence or insertion point.
        start, end = p.span
        if p.op == "replace":
            inside = any(s.span[0] <= start and end <= s.span[1] for s in sentences)
            if not inside or "\n" in new or not new.strip():
                failures[p.id].append("Test 5: the replacement is not confined to one sentence.")
        elif p.op == "delete":
            removed = text[start:end].strip().strip(" -*•·▪◦‣○●■□➢➤✓✔").strip()
            if removed not in {s.text for s in sentences}:
                failures[p.id].append("Test 5: the deletion is not exactly one sentence.")
        else:
            at_line_end = start == len(text) or text[start] == "\n"
            if not at_line_end or not new.startswith("\n") or "\n" in new.lstrip("\n"):
                failures[p.id].append("Test 5: the insertion is not a new line at a line end.")
    return failures


# The Refiner


def _rewrite(c: _Context, sentence: str, feedback: list[str] | None = None) -> str | None:
    if not feedback and sentence in c.rewrites:  # verified for this check before
        return c.rewrites[sentence]
    rules = {rule.id: rule for rule in c.pack.rules}
    system = (PROMPTS_DIR / "rewrite.md").read_text(encoding="utf-8").replace("{{ON-CEX-01}}", rule_block(rules["ON-CEX-01"]))
    user = f"<sentence>{sentence}</sentence>"
    if feedback:
        user += "\n\nA previous rewrite failed these checks:\n" + "\n".join(f"- {f}" for f in feedback) + "\nWrite a new one."
    try:
        out = c.llm.parse(system=system, user=user, schema=_Rewrite, settings=c.rewrite_settings).sentence
    except LLMError:
        return None
    out = re.sub(r"\s+", " ", fold(out)).strip()
    return out if out and out != sentence else None


def _check(c: _Context, patches: list[Patch]) -> dict[str, list[str]]:
    if not patches:
        return {}
    try:
        after, applied = reinspect(c, patches)
    except (_Unstable, ValueError) as error:
        return {p.id: [f"Test 3: {error}."] for p in patches}
    except LLMError as error:  # a rewritten sentence could not be re-read: fail closed on the LLM patches
        return {p.id: [f"Test 1: the rewritten sentence could not be re-checked ({error})."] for p in patches if p.writer == "llm"}
    return acceptance(c, patches, after, applied)


def _verify_options(c: _Context, patch: Patch) -> list[str]:
    """Keep the range options that fix their own range and pass tests 3 and 5."""
    kept = []
    for option in patch.options:
        trial = patch.model_copy(update={"after": option})
        after, applied = reinspect(c, [trial])
        failures = acceptance(c, [trial], after, applied).get(trial.id, [])
        result = next(r for r in after.report.results if r.rule == "ON-PAY-02")
        fixed = result.verdict in _FIXED or not any(_overlaps(applied.spans[trial.id], e) for e in result.evidence)
        if fixed and not [f for f in failures if not f.startswith("Test 1")]:
            kept.append(option)
    return kept


def _to_original(doc: NormalisedText, patch: Patch) -> Span:
    start, end = patch.span
    if patch.op == "insert":
        position = doc.offsets[start - 1] + 1 if start > 0 else 0
        return (position, position)
    return doc.to_original(patch.span)


def refine(
    base: Inspection,
    ctx: Context,
    posting_date: date,
    pack: RulePack,
    llm: StructuredLLM,
    *,
    variant: Variant = "formal",
    classify_settings: ModelSettings = ModelSettings(),
    rewrite_settings: ModelSettings = REWRITE_SETTINGS,
    label_cache: dict[str, SentenceLabels] | None = None,
    rewrites: dict[str, str] | None = None,
) -> Refinement:
    """Pass the same label_cache and rewrites dicts on every call for one check to avoid repeat LLM calls."""
    wording = load_wording(pack.jurisdiction)
    c = _Context(base, ctx, posting_date, pack, wording, llm, classify_settings, rewrite_settings,
                 label_cache if label_cache is not None else {}, rewrites if rewrites is not None else {})  # fmt: skip
    plan = _plan(base, ctx, pack, wording, variant)
    guidance = {r.rule: (r.fix or {}).get("guidance", r.message) for r in base.report.results}

    def drop(p: Patch, failures: list[str]) -> None:
        plan.dropped.append(Dropped(rule=p.rule, span=p.span, guidance=guidance[p.rule], failures=failures))

    choices = [p for p in plan.patches if p.options]
    patches: list[Patch] = []
    for p in plan.patches:
        if p.options:
            continue
        if p.writer == "llm":
            written = _rewrite(c, p.before)
            if written is None:
                drop(p, ["The rewrite call gave no usable sentence."])
                continue
            p = p.model_copy(update={"after": written})
        patches.append(p)

    failures = _check(c, patches)
    if failures:
        retried = []
        for p in patches:
            if p.id not in failures:
                retried.append(p)
            elif p.writer == "llm" and (written := _rewrite(c, p.before, failures[p.id])) is not None:
                retried.append(p.model_copy(update={"after": written}))
            else:
                drop(p, failures[p.id])
        patches = retried
        failures = _check(c, patches)
        for p in [p for p in patches if p.id in failures]:
            drop(p, failures[p.id])
        patches = [p for p in patches if p.id not in failures]

    for p in choices:
        if kept := _verify_options(c, p):
            patches.append(p.model_copy(update={"options": kept}))
        else:
            drop(p, ["No narrower range passed the checks."])

    patches = [
        p.model_copy(update={"verified": True, "original_span": _to_original(base.document, p)})
        for p in sorted(patches, key=lambda p: int(p.id[1:]))
    ]
    c.rewrites.update({p.before: p.after for p in patches if p.writer == "llm" and p.after})
    text, report = _finish(c, [p for p in patches if p.default and p.after is not None])
    return Refinement(patches=patches, questions=plan.questions, dropped=plan.dropped, text=text, report=report)


def _finish(c: _Context, chosen: list[Patch]) -> tuple[str, Report]:
    """The pasted text with the chosen patches applied, and the verdicts on it."""
    final, _ = reinspect(c, chosen)
    original = c.base.document.original
    # Right to left; inserts at the same place go in last-planned first, so they read in plan order.
    for p in sorted(chosen, key=lambda p: (p.original_span, int(p.id[1:])), reverse=True):
        start, end = p.original_span
        original = original[:start] + (p.after or "") + original[end:]
    return original, final.report


def finalize(
    base: Inspection,
    ctx: Context,
    posting_date: date,
    pack: RulePack,
    llm: StructuredLLM,
    chosen: list[Patch],
    *,
    classify_settings: ModelSettings = ModelSettings(),
    label_cache: dict[str, SentenceLabels] | None = None,
) -> tuple[str, Report]:
    """Apply the patches the user accepted (with any option they picked); the status is recomputed on that text."""
    wording = load_wording(pack.jurisdiction)
    c = _Context(base, ctx, posting_date, pack, wording, llm, classify_settings, REWRITE_SETTINGS,
                 label_cache if label_cache is not None else {})  # fmt: skip
    return _finish(c, chosen)
