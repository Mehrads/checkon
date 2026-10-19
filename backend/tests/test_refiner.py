"""Refiner with a scripted LLM: patch types, acceptance tests, retry and drop, output text."""

from datetime import date
from decimal import Decimal
from typing import Any

from app.compliance.classification import Classification, safety_net
from app.compliance.extraction import Extraction
from app.compliance.inspector import Inspection, inspect
from app.compliance.llm import LLMError
from app.compliance.models import Context, PayMention, PayUnit
from app.compliance.money import restate_range
from app.compliance.normalise import normalise
from app.compliance.refiner import Patch, _deletion, _Rewrite, apply_edits, range_options, refine
from app.compliance.rulepack import load_pack
from tests.fake_llm import FakeLLM

PACK = load_pack("CA-ON")
POSTED = date(2026, 10, 19)
PARAMS = next(r for r in PACK.rules if r.id == "ON-PAY-02").params

POSTING = """Payroll Specialist
Mississauga, ON (hybrid)

Requirements:
• 2+ years of Canadian payroll experience
• Excellent communication skills

Compensation
Salary: $60,000 – $80,000 per year.

This posting is for an existing vacancy.
"""


def sid(text: str, fragment: str) -> int:
    return next(s.id for s in normalise(text).sentences if fragment in s.text)


def extraction(text: str, **changes: Any) -> dict[str, Any]:
    pay = []
    if "$60,000 - $80,000 per year" in normalise(text).text:
        pay = [{"sentence": sid(text, "Salary"), "quote": "$60,000 - $80,000 per year", "min": 60000, "max": 80000,
                "unit": "year", "kind": "wage"}]  # fmt: skip
    base = {
        "input_kind": "one_posting", "contains_french": False, "title": "Payroll Specialist",
        "locations": ["Mississauga, ON"], "work_in_ontario": True, "internal_only": False, "specific_position": True,
        "pay": pay, "vacancy_sentences": [], "ai_sentences": [], "requirement_sentences": [],
    }  # fmt: skip
    return {**base, **changes}


def labels(cex: dict[int, str] | None = None, vacancy: dict[int, str] | None = None, ai: dict[int, str] | None = None):
    return {
        "canadian_experience": [{"sentence": i, "label": label, "reason": "r"} for i, label in (cex or {}).items()],
        "vacancy": [{"sentence": i, "label": label, "reason": "r"} for i, label in (vacancy or {}).items()],
        "ai": [{"sentence": i, "label": label, "reason": "r"} for i, label in (ai or {}).items()],
    }


def inspected(text: str, ctx: Context, extraction_changes: dict, label_answer: dict) -> Inspection:
    # Sentences the keyword safety net adds ("Canadian ...") are labelled ok unless the test says otherwise.
    given = {label["sentence"] for label in label_answer["canadian_experience"]}
    extra = [{"sentence": i, "label": "ok", "reason": "r"} for i in sorted(safety_net(normalise(text))) if i not in given]
    label_answer = {**label_answer, "canadian_experience": label_answer["canadian_experience"] + extra}
    llm = FakeLLM().queue(Extraction, extraction(text, **extraction_changes)).queue(Classification, label_answer)
    return inspect(text, ctx, POSTED, PACK, llm)


def requirement_posting(ctx: Context, cex_label: str = "violation") -> Inspection:
    canadian, skills = sid(POSTING, "Canadian"), sid(POSTING, "communication")
    vacancy = sid(POSTING, "existing vacancy")
    return inspected(
        POSTING,
        ctx,
        {"requirement_sentences": [canadian, skills], "vacancy_sentences": [vacancy]},
        labels(cex={canadian: cex_label, skills: "ok"}, vacancy={vacancy: "existing"}),
    )


CTX = Context(meets_headcount_threshold=True, uses_ai_in_hiring=False, existing_vacancy=True)


def verdicts(report) -> dict[str, str]:
    return {r.rule: r.verdict.value for r in report.results}


def rewrite_llm(*sentences: str | Exception, relabel: list[str] | None = None) -> FakeLLM:
    llm = FakeLLM()
    for sentence in sentences:
        llm.queue(_Rewrite, sentence if isinstance(sentence, Exception) else {"sentence": sentence})
    for label in relabel or []:
        llm.queue(Classification, labels(cex={sid(POSTING, "payroll experience"): label}))
    return llm


# Canadian experience: LLM rewrite of one sentence


def test_rewrite_fixes_the_finding_and_keeps_the_rest_byte_identical() -> None:
    base = requirement_posting(CTX)
    llm = rewrite_llm("2+ years of payroll experience", relabel=["ok"])
    result = refine(base, CTX, POSTED, PACK, llm)

    [patch] = result.patches
    assert (patch.rule, patch.op, patch.writer, patch.verified, patch.default) == ("ON-CEX-01", "replace", "llm", True, True)
    assert patch.before == "2+ years of Canadian payroll experience"
    assert patch.after == "2+ years of payroll experience"
    assert verdicts(result.report)["ON-CEX-01"] == "pass"
    assert result.report.status == "compliant"
    assert result.text == POSTING.replace("2+ years of Canadian payroll experience", "2+ years of payroll experience")
    assert POSTING[patch.original_span[0] : patch.original_span[1]] == patch.before


def test_rewrite_that_still_violates_is_retried_with_feedback() -> None:
    base = requirement_posting(CTX)
    llm = rewrite_llm("2+ years of payroll experience in Canada", "2+ years of payroll experience", relabel=["violation", "ok"])
    result = refine(base, CTX, POSTED, PACK, llm)

    retry = llm.calls_for(_Rewrite)[1].user
    assert "Test 1: ON-CEX-01 is still fail" in retry
    assert result.patches[0].after == "2+ years of payroll experience"
    assert result.dropped == []


def test_rewrite_that_adds_a_fact_is_dropped_after_one_retry() -> None:
    base = requirement_posting(CTX)
    invented = "2+ years of payroll experience with SAP"
    llm = rewrite_llm(invented, invented, relabel=["ok"])
    result = refine(base, CTX, POSTED, PACK, llm)

    assert result.patches == []
    [dropped] = result.dropped
    assert dropped.rule == "ON-CEX-01"
    assert any("Test 4" in f and "SAP" in f for f in dropped.failures)
    assert dropped.guidance.startswith("Ask for the skill")
    assert verdicts(result.report)["ON-CEX-01"] == "fail"
    assert result.text == POSTING


def test_failed_rewrite_call_drops_the_patch() -> None:
    base = requirement_posting(CTX)
    result = refine(base, CTX, POSTED, PACK, rewrite_llm(LLMError("declined")))
    assert result.patches == []
    assert result.dropped[0].rule == "ON-CEX-01"


def test_borderline_rewrite_is_a_suggestion_not_applied_by_default() -> None:
    base = requirement_posting(CTX, cex_label="borderline")
    llm = rewrite_llm("2+ years of payroll experience", relabel=["ok"])
    result = refine(base, CTX, POSTED, PACK, llm)

    [patch] = result.patches
    assert patch.verified and patch.default is False
    assert verdicts(result.report)["ON-CEX-01"] == "warning"
    assert result.text == POSTING


# Pay


def no_pay_posting() -> Inspection:
    text = POSTING.replace("Salary: $60,000 – $80,000 per year.", "Great benefits and a friendly team.")
    vacancy = sid(text, "existing vacancy")
    return inspected(text, CTX, {"vacancy_sentences": [vacancy]}, labels(vacancy={vacancy: "existing"}))


def test_missing_pay_gets_the_placeholder_in_the_pay_section() -> None:
    base = no_pay_posting()
    assert verdicts(base.report)["ON-PAY-01"] == "fail"
    result = refine(base, CTX, POSTED, PACK, FakeLLM())

    [patch] = result.patches
    assert (patch.rule, patch.op, patch.writer) == ("ON-PAY-01", "insert", "template")
    pay = next(r for r in result.report.results if r.rule == "ON-PAY-01")
    assert pay.verdict == "needs_input" and pay.question.id == "expected_pay"
    assert "Great benefits and a friendly team.\n[Pay range: add before publishing]\n\nThis posting" in result.text


def test_wide_range_offers_options_and_applies_none() -> None:
    text = POSTING.replace("$80,000", "$120,000")
    pay = [{"sentence": sid(text, "Salary"), "quote": "$60,000 - $120,000 per year", "min": 60000, "max": 120000,
            "unit": "year", "kind": "wage"}]  # fmt: skip
    vacancy = sid(text, "existing vacancy")
    base = inspected(text, CTX, {"pay": pay, "vacancy_sentences": [vacancy]}, labels(vacancy={vacancy: "existing"}))
    assert verdicts(base.report)["ON-PAY-02"] == "fail"
    result = refine(base, CTX, POSTED, PACK, FakeLLM())

    [patch] = result.patches
    assert patch.after is None and patch.default is False and patch.writer == "code"
    assert patch.options == [
        "$60,000 - $110,000 per year",
        "$65,000 - $115,000 per year",
        "$70,000 - $120,000 per year",
    ]
    assert verdicts(result.report)["ON-PAY-02"] == "fail"  # nothing is applied until the employer picks
    assert result.text == text


def test_range_options_for_an_hourly_range() -> None:
    pay = PayMention(min=Decimal(25), max=Decimal(50), unit=PayUnit.HOUR, span=(0, 10))
    options = range_options(pay, Context(hours_per_week=Decimal(40)), PARAMS)
    assert options == [(25, 49), (Decimal("25.50"), Decimal("49.50")), (26, 50)]
    for low, high in options:
        assert (high - low) * 40 * 52 <= 50000


def test_restate_range_keeps_the_original_style() -> None:
    assert restate_range("$60k-120k a year", Decimal(65000), Decimal(115000)) == "$65k-115k a year"
    assert restate_range("$60-120K", Decimal(65000), Decimal(115000)) == "$65-115K"
    assert restate_range("$25 - $50/hr", Decimal("25.5"), Decimal("49.5")) == "$25.50 - $49.50/hr"
    assert restate_range("$70,000+", Decimal(1), Decimal(2)) is None


# Statements from the wording library


def statement_posting(ctx: Context, ai_sentence: str | None = None) -> Inspection:
    text = POSTING.replace("\nThis posting is for an existing vacancy.\n", "\n")
    ai = {}
    if ai_sentence:
        text = text.replace("• Excellent communication skills", f"• Excellent communication skills\n{ai_sentence}")
        ai = {sid(text, ai_sentence[:20]): "uses_ai"}
    return inspected(text, ctx, {"ai_sentences": list(ai)}, labels(ai=ai))


def test_missing_vacancy_statement_asks_first() -> None:
    ctx = Context(meets_headcount_threshold=True, uses_ai_in_hiring=False)
    result = refine(statement_posting(ctx), ctx, POSTED, PACK, FakeLLM())
    assert result.patches == []
    assert [q.id for q in result.questions] == ["existing_vacancy"]


def test_vacancy_and_ai_statements_come_from_the_library_in_rule_order() -> None:
    ctx = Context(meets_headcount_threshold=True, uses_ai_in_hiring=True, existing_vacancy=False)
    base = statement_posting(ctx)
    assert verdicts(base.report)["ON-AI-01"] == "fail"
    result = refine(base, ctx, POSTED, PACK, FakeLLM(), variant="plain")

    assert [(p.rule, p.writer) for p in result.patches] == [("ON-VAC-01", "wording_library"), ("ON-AI-01", "wording_library")]
    # The pasted text's own trailing blank line stays after the inserted statements.
    assert result.text.endswith(
        "Salary: $60,000 – $80,000 per year.\n\n"
        "This job is not an existing vacancy.\n\n"
        "We use AI tools to help screen, assess or select applicants.\n\n"
    )
    assert verdicts(result.report)["ON-VAC-01"] == "pass"
    assert verdicts(result.report)["ON-AI-01"] == "pass"


def test_inaccurate_ai_statement_is_removed_with_its_line() -> None:
    sentence = "We use AI tools to screen applications."
    base = statement_posting(CTX, ai_sentence=sentence)
    assert verdicts(base.report)["ON-AI-01"] == "warning"
    result = refine(base, CTX, POSTED, PACK, FakeLLM())

    [patch] = [p for p in result.patches if p.rule == "ON-AI-01"]  # the vacancy statement is added too
    assert (patch.op, patch.writer) == ("delete", "code")
    assert sentence not in result.text
    assert "• Excellent communication skills\n\nCompensation" in result.text
    assert verdicts(result.report)["ON-AI-01"] == "pass"


# Mechanics


def test_apply_edits_moves_untouched_spans() -> None:
    text = "aaa bbb ccc"
    patches = [
        Patch(id="p1", rule="R", op="replace", span=(4, 7), before="bbb", after="BBBBB", writer="code"),
        Patch(id="p2", rule="R", op="insert", span=(11, 11), before="", after="\n\nend", writer="code"),
    ]
    applied = apply_edits(text, patches)
    assert applied.text == "aaa BBBBB ccc\n\nend"
    assert applied.spans == {"p1": (4, 9), "p2": (13, 18)}
    assert (applied.start(8), applied.end(11)) == (10, 13)  # "ccc" moved by +2; the insert sits after it
    assert applied.touched((4, 7)) and not applied.touched((0, 3))


def test_deleting_a_paragraph_leaves_no_triple_blank_line() -> None:
    text = "First line.\n\nRemove me.\n\nLast line."
    start, end = _deletion(text, (13, 23))
    assert text[:start] + text[end:] == "First line.\n\nLast line."


def test_compliant_posting_needs_no_patches() -> None:
    base = requirement_posting(CTX, cex_label="ok")
    result = refine(base, CTX, POSTED, PACK, FakeLLM())
    assert result.patches == result.dropped == result.questions == []
    assert result.text == POSTING
    assert result.report.status == "compliant"
