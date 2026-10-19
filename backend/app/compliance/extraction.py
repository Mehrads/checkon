"""Fact extraction, span verification and the pay cross-check (Technical Design §4, steps 2–4).

The LLM refers to sentences by number and copies text for anything smaller than a sentence.
Code then checks every reference: a quote must exist verbatim, a sentence number must exist, and each
pay figure must match the deterministic parser's reading. Anything that fails is sent back once as
feedback; whatever still fails is dropped, or for pay, marked as a disagreement for the user to settle.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from app.compliance.llm import ModelSettings, StructuredLLM
from app.compliance.models import PayKind, PayMention, PayUnit, Span, TextFact
from app.compliance.money import PayReading, format_pay
from app.compliance.normalise import NormalisedText

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


class PayItem(BaseModel):
    sentence: int
    quote: str
    min: float | None
    max: float | None
    unit: Literal["hour", "week", "month", "year"] | None
    kind: Literal["wage", "commission", "bonus", "equity", "benefits"]


class Extraction(BaseModel):
    input_kind: Literal["one_posting", "multiple_postings", "not_a_posting"]
    contains_french: bool
    title: str | None
    locations: list[str]
    work_in_ontario: bool | None
    internal_only: bool | None
    specific_position: bool | None
    pay: list[PayItem]
    vacancy_sentences: list[int]
    ai_sentences: list[int]
    requirement_sentences: list[int]


@dataclass
class Verified:
    extraction: Extraction
    title: TextFact | None = None
    locations: list[TextFact] = field(default_factory=list)
    pay: list[PayMention] = field(default_factory=list)
    vacancy_ids: list[int] = field(default_factory=list)
    ai_ids: list[int] = field(default_factory=list)
    requirement_ids: list[int] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def render_posting(doc: NormalisedText) -> str:
    lines: list[str] = []
    for section in doc.sections:
        if section.heading:
            lines.append(f"## {section.heading.value}")
        lines.extend(f"[{s.id}] {s.text}" for s in doc.sentences if s.section == section.id)
    return "\n".join(lines)


def extract(
    doc: NormalisedText, llm: StructuredLLM, settings: ModelSettings, feedback: list[str] | None = None
) -> Extraction:
    user = f"<posting>\n{render_posting(doc)}\n</posting>"
    if feedback:
        problems = "\n".join(f"- {problem}" for problem in feedback)
        user += (
            "\n\nA previous answer for this posting had these problems:\n"
            f"<problems>\n{problems}\n</problems>\n"
            "Give a complete new answer that fixes them. Copy quotes exactly from the posting."
        )
    system = (PROMPTS_DIR / "extract.md").read_text(encoding="utf-8")
    return llm.parse(system=system, user=user, schema=Extraction, settings=settings)


def _overlaps(a: Span, b: Span) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def _decimal(value: float | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _locate(doc: NormalisedText, quote: str, within: Span | None = None) -> Span | None:
    quote = quote.strip()
    if not quote:
        return None
    if within:
        start = doc.text.find(quote, within[0], within[1])
        if start >= 0:
            return (start, start + len(quote))
    start = doc.text.find(quote)
    return (start, start + len(quote)) if start >= 0 else None


def _same_reading(item: PayItem, reading: PayReading) -> bool:
    return (
        _decimal(item.min) == reading.min
        and _decimal(item.max) == reading.max
        and reading.unit is not None
        and item.unit == reading.unit.value
    )


def verify(doc: NormalisedText, extraction: Extraction, readings: list[PayReading]) -> Verified:
    out = Verified(extraction=extraction)
    sentences = {s.id: s for s in doc.sentences}

    def known(ids: list[int]) -> list[int]:
        for missing in sorted(set(ids) - sentences.keys()):
            out.problems.append(f"Sentence [{missing}] does not exist.")
        return sorted(set(ids) & sentences.keys())

    out.vacancy_ids = known(extraction.vacancy_sentences)
    out.ai_ids = known(extraction.ai_sentences)
    out.requirement_ids = known(extraction.requirement_sentences)

    if extraction.title:
        span = _locate(doc, extraction.title)
        if span:
            out.title = TextFact(value=doc.text[span[0] : span[1]], span=span)
        else:
            out.problems.append(f'The title "{extraction.title}" is not in the posting word for word.')
    for location in extraction.locations:
        span = _locate(doc, location)
        if span:
            out.locations.append(TextFact(value=doc.text[span[0] : span[1]], span=span))
        else:
            out.problems.append(f'The location "{location}" is not in the posting word for word.')

    matched: set[int] = set()
    for item in extraction.pay:
        if item.min is None and item.max is None:
            out.problems.append(f'The pay quote "{item.quote}" has no numbers.')
            continue
        sentence = sentences.get(item.sentence)
        span = _locate(doc, item.quote, sentence.span if sentence else None)
        if span is None:
            out.problems.append(f'The pay quote "{item.quote}" is not in the posting word for word.')
            continue
        reading = next((r for r in readings if _overlaps(span, r.span)), None)
        if reading is not None:
            matched.add(readings.index(reading))
        # Only base pay feeds the pay rules, so only wages need the second reading to agree.
        agree = item.kind != "wage" or (reading is not None and _same_reading(item, reading))
        alternate = None
        if not agree:
            alternate = format_pay(reading.min, reading.max, reading.unit) if reading else None
            mine = format_pay(_decimal(item.min), _decimal(item.max), _unit(item.unit))
            out.problems.append(
                f'For "{item.quote}" you gave {mine}, but a second reading gives {alternate or "no amount"}. '
                "Check the numbers and the pay period."
            )
        unit = _unit(item.unit) or (reading.unit if reading else None)
        out.pay.append(
            PayMention(
                min=_decimal(item.min),
                max=_decimal(item.max),
                unit=unit or PayUnit.YEAR,  # placeholder only when the readings disagree
                kind=PayKind(item.kind),
                span=span,
                parsers_agree=agree,
                alternate_reading=alternate,
            )
        )
    for i, reading in enumerate(readings):
        if i not in matched:
            out.problems.append(
                f'The posting also has the amount "{reading.text}". List it under pay if it describes what the job pays.'
            )
    return out


def _unit(value: str | None) -> PayUnit | None:
    return PayUnit(value) if value else None
