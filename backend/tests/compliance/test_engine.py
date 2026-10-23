"""What the report says, beyond the verdicts: messages, questions, evidence and fix hints."""

from datetime import date

from app.compliance.engine import evaluate
from app.compliance.models import Context, Facts, Report, RuleResult
from app.compliance.rulepack import load_pack

PACK = load_pack("CA-ON")
POSTED = date(2026, 10, 19)
COVERED = {"meets_headcount_threshold": True, "uses_ai_in_hiring": False}
POSTING = {
    "specific_position": True,
    "internal_only": False,
    "work_in_ontario": True,
    "pay": [{"min": 60000, "max": 80000, "unit": "year", "span": [100, 120]}],
    "vacancy_statement": {"present": True, "polarity": "existing", "span": [200, 240]},
}


def report(facts: dict | None = None, context: dict | None = None) -> Report:
    return evaluate(
        Facts.model_validate({**POSTING, **(facts or {})}),
        Context.model_validate({**COVERED, **(context or {})}),
        PACK,
        POSTED,
    )


def result(rep: Report, rule: str) -> RuleResult:
    return next(r for r in rep.results if r.rule == rule)


def test_width_message_shows_dollar_amounts() -> None:
    rep = report({"pay": [{"min": 25, "max": 50, "unit": "hour", "span": [100, 120]}]}, {"hours_per_week": 40})
    assert result(rep, "ON-PAY-02").message == "The pay range is $52,000 a year wide; the limit is $50,000."


def test_open_ended_message_describes_the_pay() -> None:
    rep = report({"pay": [{"min": 70000, "unit": "year", "span": [100, 120]}]})
    assert "($70,000+ a year)" in result(rep, "ON-PAY-02").message


def test_needs_input_carries_the_question() -> None:
    rep = report(context={"uses_ai_in_hiring": None})
    question = result(rep, "ON-AI-01").question
    assert question is not None
    assert question.id == "uses_ai_in_hiring"
    assert question.text.startswith("Do you, or a recruiter acting for you, use AI to screen, assess or select applicants")


def test_headcount_question_uses_the_threshold_from_the_pack() -> None:
    rep = report(context={"meets_headcount_threshold": None})
    question = result(rep, "ON-APPL-01").question
    assert question is not None
    assert question.text.startswith("Does your company have 25 or more employees in Ontario on the day the job is posted?")


def test_hours_question_for_near_cap_hourly_range() -> None:
    rep = report({"pay": [{"min": 25, "max": 48, "unit": "hour", "span": [100, 120]}]})
    pay = result(rep, "ON-PAY-02")
    assert pay.question is not None and pay.question.id == "hours_per_week"
    assert "$47,840" in pay.message


def test_every_violating_sentence_is_evidence() -> None:
    rep = report(
        {
            "requirements": [
                {"text": "Canadian experience required", "span": [300, 329], "cex_label": "violation"},
                {"text": "Excel skills", "span": [330, 342], "cex_label": "ok"},
                {"text": "Must have worked in Canada", "span": [343, 369], "cex_label": "violation"},
            ]
        }
    )
    assert result(rep, "ON-CEX-01").evidence == [(300, 329), (343, 369)]


def test_fix_hint_only_on_fail_or_warning() -> None:
    rep = report({"vacancy_statement": {"present": False}})
    fix = result(rep, "ON-VAC-01").fix
    assert fix is not None
    assert (fix["type"], fix["writer"]) == ("insert", "wording_library")
    assert result(rep, "ON-PAY-01").fix is None


def test_fix_guidance_is_rendered_with_params() -> None:
    rep = report({"pay": [{"min": 60000, "max": 120000, "unit": "year", "span": [100, 120]}]})
    guidance = result(rep, "ON-PAY-02").fix["guidance"]
    assert guidance == "Give a minimum and a maximum no more than $50,000 a year apart."


def test_gate_reason_is_the_report_message() -> None:
    rep = report(context={"headcount": 18})
    assert rep.message is not None
    assert "25 or more employees" in rep.message
    assert result(rep, "ON-PAY-01").message == rep.message


def test_report_records_the_rule_pack_version() -> None:
    assert report().versions == {"rule_pack": "CA-ON@1.2.0"}


def test_process_rules_are_reminders_not_results() -> None:
    rep = report()
    assert {r.rule for r in rep.results} == {
        "ON-APPL-01", "ON-APPL-02", "ON-PAY-01", "ON-PAY-02", "ON-VAC-01", "ON-AI-01", "ON-CEX-01",
    }  # fmt: skip
    assert [r.rule for r in rep.reminders] == ["ON-INT-01", "ON-REC-01"]


def test_reminders_carry_the_plain_line_and_the_citation() -> None:
    reminders = {r.rule: r for r in report().reminders}
    interview = reminders["ON-INT-01"]
    assert interview.text.startswith("Within 45 days of an interview (or the last one), tell the applicant")
    assert interview.citation.startswith("ESA 2000, s. 8.6; O. Reg. 476/24, s. 5")
    records = reminders["ON-REC-01"]
    assert records.text.startswith("Keep a copy of this posting, every revised version, any linked document")
    assert records.citation.startswith("ESA 2000, s. 15 (7.1) and (7.1.1)")


def test_reminders_are_listed_whatever_the_verdicts() -> None:
    failing = report({"vacancy_statement": {"present": False}, "pay": []})
    assert failing.status == "not_compliant"
    asking = report(context={"meets_headcount_threshold": None})
    assert asking.status == "needs_input"
    for rep in (failing, asking):
        assert [r.rule for r in rep.reminders] == ["ON-INT-01", "ON-REC-01"]


def test_no_reminders_when_the_rules_dont_apply() -> None:
    small = report(context={"headcount": 18})
    internal = report({"internal_only": True})
    early = evaluate(Facts.model_validate(POSTING), Context.model_validate(COVERED), PACK, date(2025, 12, 31))
    for rep in (small, internal, early):
        assert rep.status == "not_applicable"
        assert rep.reminders == []
