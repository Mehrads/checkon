"""Rule checks as pure functions over facts, context and the rule's params (Technical Design §4, step 7).

A check returns an Outcome: the verdict plus the message key, values, evidence and question id.
All wording and every legal number live in the rule pack; checks only decide.
"""

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import Any

from app.compliance.models import Context, Facts, PayKind, PayMention, PayUnit, Span, Verdict
from app.compliance.money import format_pay


@dataclass(frozen=True)
class Outcome:
    verdict: Verdict
    key: str | None = None  # message key in the rule record; defaults to the verdict
    values: dict[str, Any] = field(default_factory=dict)
    evidence: list[Span] = field(default_factory=list)
    question: str | None = None  # question id in the rule record


Check = Callable[[Facts, Context, dict[str, Any]], Outcome]
CHECKS: dict[str, Check] = {}

# Most severe first: one rule with several findings reports the worst.
SEVERITY = [Verdict.FAIL, Verdict.NEEDS_INPUT, Verdict.WARNING, Verdict.PASS, Verdict.NOT_APPLICABLE]


def check(name: str) -> Callable[[Check], Check]:
    def register(fn: Check) -> Check:
        CHECKS[name] = fn
        return fn

    return register


def worst(outcomes: list[Outcome]) -> Outcome:
    top = min(outcomes, key=lambda outcome: SEVERITY.index(outcome.verdict))
    evidence = [span for outcome in outcomes if outcome.verdict == top.verdict for span in outcome.evidence]
    return replace(top, evidence=evidence)


def _answer_or_fact(answer: bool | None, fact: bool | None) -> bool | None:
    return answer if answer is not None else fact


# Applicability


@check("employer_size")
def employer_size(facts: Facts, ctx: Context, params: dict[str, Any]) -> Outcome:
    if ctx.headcount is not None:
        meets = ctx.headcount >= params["min_employees"]
    else:
        meets = ctx.meets_headcount_threshold
    if meets is None:
        return Outcome(Verdict.NEEDS_INPUT, question="meets_headcount_threshold")
    verdict = Verdict.PASS if meets else Verdict.NOT_APPLICABLE
    if ctx.headcount_basis == "assumed":
        return Outcome(verdict, key=f"assumed_{verdict.value}")
    if ctx.headcount_basis == "search":
        return Outcome(verdict, key=f"search_{verdict.value}", values={"evidence": ctx.headcount_evidence or ""})
    return Outcome(verdict)


@check("public_posting")
def public_posting(facts: Facts, ctx: Context, params: dict[str, Any]) -> Outcome:
    specific = _answer_or_fact(ctx.specific_position, facts.specific_position)
    internal = _answer_or_fact(ctx.internal_only, facts.internal_only)
    in_ontario = _answer_or_fact(ctx.work_in_ontario, facts.work_in_ontario)
    # A definitive exclusion wins over a fact that is still unknown.
    if specific is False:
        return Outcome(Verdict.NOT_APPLICABLE, key="general_campaign")
    if internal is True:
        return Outcome(Verdict.NOT_APPLICABLE, key="internal_only")
    if in_ontario is False:
        return Outcome(Verdict.NOT_APPLICABLE, key="outside_ontario")
    for question, value in [
        ("specific_position", specific),
        ("internal_only", internal),
        ("work_in_ontario", in_ontario),
    ]:
        if value is None:
            return Outcome(Verdict.NEEDS_INPUT, question=question)
    return Outcome(Verdict.PASS)


# Pay

def _hours(ctx: Context, params: dict[str, Any]) -> Decimal:
    return ctx.hours_per_week if ctx.hours_per_week is not None else params["default_hours_per_week"]


def annualise(amount: Decimal, unit: PayUnit, hours_per_week: Decimal, params: dict[str, Any]) -> Decimal:
    weeks = params["weeks_per_year"]
    match unit:
        case PayUnit.HOUR:
            return amount * hours_per_week * weeks
        case PayUnit.WEEK:
            return amount * weeks
        case PayUnit.MONTH:
            return amount * 12
        case PayUnit.YEAR:
            return amount


def describe(pay: PayMention) -> str:
    return format_pay(pay.min, pay.max, pay.unit)


def _top_annual(pay: PayMention, ctx: Context, params: dict[str, Any]) -> Decimal:
    top = pay.max if pay.max is not None else pay.min
    return annualise(top, pay.unit, _hours(ctx, params), params)


def _above_threshold(pay: PayMention, ctx: Context, params: dict[str, Any]) -> bool:
    return _top_annual(pay, ctx, params) > params["exemption_threshold_annual"]


def _exempt(wages: list[PayMention], ctx: Context, params: dict[str, Any]) -> bool:
    """O. Reg. 476/24, s. 3: expected pay, or the top of the range, equivalent to more than the threshold a year.

    The posted pay shows it on its own when it is stated by the year, month or week, or by the hour with the
    hours known. Otherwise the employer's answer decides: hourly pay with unknown hours, or no pay in the text.
    """
    readable = [pay for pay in wages if pay.parsers_agree]
    if ctx.pay_exemption_confirmed is False:
        return False
    if ctx.pay_exemption_confirmed is True:
        return not wages or any(_above_threshold(pay, ctx, params) for pay in readable)
    return any(
        _above_threshold(pay, ctx, params)
        for pay in readable
        if pay.unit != PayUnit.HOUR or ctx.hours_per_week is not None
    )


def _disagreement(pay: PayMention) -> Outcome:
    return Outcome(
        Verdict.NEEDS_INPUT,
        key="parsers_disagree",
        values={"reading": describe(pay), "alternate": pay.alternate_reading or "something else"},
        evidence=[pay.span],
        question="pay_reading",
    )


@check("pay_disclosed")
def pay_disclosed(facts: Facts, ctx: Context, params: dict[str, Any]) -> Outcome:
    wages = [pay for pay in facts.pay if pay.kind == PayKind.WAGE]
    if _exempt(wages, ctx, params):
        return Outcome(Verdict.NOT_APPLICABLE, key="exempt", evidence=[pay.span for pay in wages])
    unreadable = [pay for pay in wages if not pay.parsers_agree]
    if unreadable:
        return _disagreement(unreadable[0])
    if wages:
        return Outcome(Verdict.PASS, evidence=[pay.span for pay in wages])
    if facts.pay_placeholder:
        return Outcome(
            Verdict.NEEDS_INPUT, key="placeholder", evidence=[facts.pay_placeholder], question="expected_pay"
        )
    commission = [pay for pay in facts.pay if pay.kind == PayKind.COMMISSION]
    if commission:
        return Outcome(
            Verdict(params["commission_only_verdict"]),
            key="commission_only",
            evidence=[pay.span for pay in commission],
        )
    if facts.pay:
        return Outcome(Verdict.FAIL, key="no_wages", evidence=[pay.span for pay in facts.pay])
    return Outcome(Verdict.FAIL)


def _range_width(pay: PayMention, ctx: Context, params: dict[str, Any]) -> Outcome:
    if not pay.parsers_agree:
        return _disagreement(pay)
    if pay.min is None or pay.max is None:
        return Outcome(Verdict.FAIL, key="open_ended", values={"reading": describe(pay)}, evidence=[pay.span])

    cap = params["max_annual_width"]
    width = annualise(pay.max - pay.min, pay.unit, _hours(ctx, params), params)
    values = {"width": width}
    hours_unknown = pay.unit == PayUnit.HOUR and ctx.hours_per_week is None
    if hours_unknown and abs(width - cap) <= cap * params["near_cap_margin"]:
        return Outcome(
            Verdict.NEEDS_INPUT, key="hours_unknown", values=values, evidence=[pay.span], question="hours_per_week"
        )
    if width <= cap:
        return Outcome(Verdict.PASS, values=values, evidence=[pay.span])
    # Only hourly pay with unknown hours reaches here with a top above the threshold (see _exempt).
    if _above_threshold(pay, ctx, params) and ctx.pay_exemption_confirmed is None:
        return Outcome(
            Verdict.NEEDS_INPUT,
            key="confirm_exemption",
            values=values,
            evidence=[pay.span],
            question="pay_exemption_confirmed",
        )
    return Outcome(Verdict.FAIL, values=values, evidence=[pay.span])


@check("pay_range_width")
def pay_range_width(facts: Facts, ctx: Context, params: dict[str, Any]) -> Outcome:
    wages = [pay for pay in facts.pay if pay.kind == PayKind.WAGE]
    if not wages:
        return Outcome(Verdict.NOT_APPLICABLE, key="no_range")
    if _exempt(wages, ctx, params):
        return Outcome(Verdict.NOT_APPLICABLE, key="exempt", evidence=[pay.span for pay in wages])
    ranges = [pay for pay in wages if not (pay.min is not None and pay.min == pay.max)]
    if not ranges:
        return Outcome(Verdict.PASS, key="single_figure", evidence=[pay.span for pay in wages])
    return worst([_range_width(pay, ctx, params) for pay in ranges])


# Statements


@check("vacancy_statement")
def vacancy_statement(facts: Facts, ctx: Context, params: dict[str, Any]) -> Outcome:
    statement = facts.vacancy_statement
    if not statement.present:
        return Outcome(Verdict.FAIL)
    evidence = [statement.span] if statement.span else []
    if statement.polarity in ("existing", "not_existing"):
        return Outcome(Verdict.PASS, evidence=evidence)
    return Outcome(Verdict.WARNING, key="vague", evidence=evidence)


@check("ai_disclosure")
def ai_disclosure(facts: Facts, ctx: Context, params: dict[str, Any]) -> Outcome:
    statement = facts.ai_disclosure
    evidence = [statement.span] if statement.present and statement.span else []
    discloses = statement.present and statement.polarity == "uses_ai"
    match ctx.uses_ai_in_hiring:
        case True if discloses:
            return Outcome(Verdict.PASS, evidence=evidence)
        case True if statement.present:
            return Outcome(Verdict.FAIL, key="contradicts", evidence=evidence)
        case True:
            return Outcome(Verdict.FAIL)
        case False if discloses:
            return Outcome(Verdict.WARNING, key="inaccurate", evidence=evidence)
        case False:
            return Outcome(Verdict.PASS, key="not_needed")
    # AI use unknown: a disclosure already satisfies the rule either way.
    if discloses:
        return Outcome(Verdict.PASS, evidence=evidence)
    return Outcome(Verdict.NEEDS_INPUT, question="uses_ai_in_hiring")


@check("canadian_experience")
def canadian_experience(facts: Facts, ctx: Context, params: dict[str, Any]) -> Outcome:
    violations = [req.span for req in facts.requirements if req.cex_label == "violation"]
    if violations:
        return Outcome(Verdict.FAIL, evidence=violations)
    borderline = [req.span for req in facts.requirements if req.cex_label == "borderline"]
    if borderline:
        return Outcome(Verdict.WARNING, evidence=borderline)
    return Outcome(Verdict.PASS)
