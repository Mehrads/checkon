"""Data contracts between the Inspector, the rule engine and the Refiner (Technical Design §6)."""

from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

Span = tuple[int, int]


class Verdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NEEDS_INPUT = "needs_input"
    NOT_APPLICABLE = "not_applicable"


class Status(StrEnum):
    COMPLIANT = "compliant"
    NOT_COMPLIANT = "not_compliant"
    NEEDS_INPUT = "needs_input"
    NOT_APPLICABLE = "not_applicable"


class PayUnit(StrEnum):
    HOUR = "hour"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class PayKind(StrEnum):
    WAGE = "wage"
    COMMISSION = "commission"
    BONUS = "bonus"
    EQUITY = "equity"
    BENEFITS = "benefits"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TextFact(_Model):
    value: str
    span: Span


class PayAlternative(_Model):
    """The deterministic parser's reading of the same pay, kept when the two readings disagree."""

    min: Decimal | None = None
    max: Decimal | None = None
    unit: PayUnit | None = None


class PayMention(_Model):
    """One pay figure or range. min == max is a single figure; a missing side is open-ended."""

    min: Decimal | None = None
    max: Decimal | None = None
    unit: PayUnit
    currency: str = "CAD"
    kind: PayKind = PayKind.WAGE
    span: Span
    parsers_agree: bool = True
    alternate_reading: str | None = None
    alternate: PayAlternative | None = None


class VacancyStatement(_Model):
    present: bool = False
    polarity: Literal["existing", "not_existing", "vague"] | None = None
    span: Span | None = None


class AIDisclosure(_Model):
    present: bool = False
    polarity: Literal["uses_ai", "no_ai"] | None = None
    span: Span | None = None


class Requirement(_Model):
    text: str
    span: Span
    cex_label: Literal["violation", "borderline", "ok"]
    reason: str | None = None


class Facts(_Model):
    """Inspector output after span verification. None means the text does not settle it."""

    title: TextFact | None = None
    locations: list[TextFact] = []
    pay: list[PayMention] = []
    vacancy_statement: VacancyStatement = VacancyStatement()
    ai_disclosure: AIDisclosure = AIDisclosure()
    requirements: list[Requirement] = []
    specific_position: bool | None = None
    internal_only: bool | None = None
    work_in_ontario: bool | None = None
    pay_placeholder: Span | None = None  # the wording-library placeholder, where pay is still to be added


class Context(_Model):
    """Company-profile facts merged with the answers given for this posting.

    None means unknown. An answer here overrides the same fact read from the text.
    """

    headcount: int | None = None
    meets_headcount_threshold: bool | None = None
    specific_position: bool | None = None
    internal_only: bool | None = None
    work_in_ontario: bool | None = None
    uses_ai_in_hiring: bool | None = None
    existing_vacancy: bool | None = None
    hours_per_week: Decimal | None = None
    pay_exemption_confirmed: bool | None = None


class Question(_Model):
    id: str
    text: str
    kind: Literal["yes_no", "number", "choice", "none"] = "yes_no"  # "none": not answerable in the check
    options: list[str] = []  # for kind "choice"; the answer is the option's index


class RuleResult(_Model):
    rule: str
    verdict: Verdict
    message: str
    evidence: list[Span] = []
    question: Question | None = None
    fix: dict[str, Any] | None = None
    citation: str
    interpretation: bool


class Report(_Model):
    status: Status
    results: list[RuleResult]
    message: str | None = None
    versions: dict[str, str]
