"""Run the applicability gate, then every content rule, and aggregate a report (Technical Design §4, steps 7–8)."""

from datetime import date
from decimal import Decimal
from typing import Any

from app.compliance.checks import CHECKS
from app.compliance.models import Context, Facts, Question, Report, RuleResult, Status, Verdict
from app.compliance.rulepack import Rule, RulePack


# How each question is answered; every other question is yes or no.
QUESTION_KINDS = {"hours_per_week": "number", "pay_reading": "choice", "expected_pay": "none"}


def _format(value: Any) -> str:
    if isinstance(value, Decimal):
        return f"{value:,.0f}" if value == value.to_integral_value() else f"{value:,.2f}"
    return str(value)


def run_rule(rule: Rule, facts: Facts, ctx: Context) -> RuleResult:
    outcome = CHECKS[rule.check](facts, ctx, rule.params)
    values = {key: _format(value) for key, value in {**rule.params, **outcome.values}.items()}
    question = None
    if outcome.question:
        kind = QUESTION_KINDS.get(outcome.question, "yes_no")
        options = [values[key] for key in ("reading", "alternate") if key in values] if kind == "choice" else []
        text = rule.questions[outcome.question].format(**values)
        question = Question(id=outcome.question, text=text, kind=kind, options=options)
    fix = None
    if rule.fix and outcome.verdict in (Verdict.FAIL, Verdict.WARNING):
        fix = {key: text.format(**values) for key, text in rule.fix.items()}
    return RuleResult(
        rule=rule.id,
        verdict=outcome.verdict,
        message=rule.messages[outcome.key or outcome.verdict.value].format(**values),
        evidence=outcome.evidence,
        question=question,
        fix=fix,
        citation=rule.citation,
        interpretation=rule.interpretation,
    )


def _not_checked(rule: Rule, reason: str) -> RuleResult:
    return RuleResult(
        rule=rule.id,
        verdict=Verdict.NOT_APPLICABLE,
        message=reason,
        citation=rule.citation,
        interpretation=rule.interpretation,
    )


def _status(gate: list[RuleResult], content: list[RuleResult]) -> Status:
    # Only fail blocks the badge outright; needs_input blocks it until answered.
    if any(result.verdict == Verdict.NEEDS_INPUT for result in gate):
        return Status.NEEDS_INPUT
    verdicts = {result.verdict for result in content}
    if Verdict.FAIL in verdicts:
        return Status.NOT_COMPLIANT
    if Verdict.NEEDS_INPUT in verdicts:
        return Status.NEEDS_INPUT
    return Status.COMPLIANT


def evaluate(facts: Facts, ctx: Context, pack: RulePack, posting_date: date) -> Report:
    rules = pack.in_force(posting_date)
    versions = {"rule_pack": pack.label}
    gate_rules = [rule for rule in rules if rule.kind == "applicability"]
    content_rules = [rule for rule in rules if rule.kind == "content"]
    if not content_rules:
        return Report(
            status=Status.NOT_APPLICABLE, results=[], message=pack.messages["not_in_force"], versions=versions
        )

    gate = [run_rule(rule, facts, ctx) for rule in gate_rules]
    excluded = next((result for result in gate if result.verdict == Verdict.NOT_APPLICABLE), None)
    if excluded:
        content = [_not_checked(rule, excluded.message) for rule in content_rules]
        return Report(
            status=Status.NOT_APPLICABLE, results=gate + content, message=excluded.message, versions=versions
        )

    content = [run_rule(rule, facts, ctx) for rule in content_rules]
    return Report(status=_status(gate, content), results=gate + content, versions=versions)
