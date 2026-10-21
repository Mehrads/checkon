"""Real calls to the Claude API (Haiku 5.5, plus Sonnet 5.5 for the rewrite).

Skipped unless RUN_LIVE_LLM=1. The key comes from ANTHROPIC_API_KEY in the repo's .env.
Both tests together cost a few cents at most; run with -s to see the measured cost.

    RUN_LIVE_LLM=1 uv run pytest tests/compliance/test_live.py -v -s
"""

import os
from collections.abc import Generator
from datetime import date
from decimal import Decimal

import anthropic
import pytest

from app.compliance.inspector import inspect
from app.compliance.llm import AnthropicLLM, SpendMeter
from app.compliance.models import Context
from app.compliance.refiner import refine
from app.compliance.rulepack import load_pack
from app.core.config import settings
from tests.compliance.test_inspector import POSTING

pytestmark = [
    pytest.mark.skipif(os.environ.get("RUN_LIVE_LLM") != "1", reason="set RUN_LIVE_LLM=1 to call the API"),
    pytest.mark.skipif(not settings.ANTHROPIC_API_KEY, reason="set ANTHROPIC_API_KEY in .env"),
]


@pytest.fixture
def llm(request: pytest.FixtureRequest) -> Generator[AnthropicLLM]:
    meter = SpendMeter()
    yield AnthropicLLM(anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY), meter=meter)
    print(f"\n{request.node.name}: ${meter.usd:.4f} in model fees")  # noqa: T201
    assert meter.usd < Decimal("0.10")


def test_live_inspection_of_the_sample_posting(llm: AnthropicLLM) -> None:
    ctx = Context(meets_headcount_threshold=True, uses_ai_in_hiring=False)
    result = inspect(POSTING, ctx, date(2026, 10, 19), load_pack("CA-ON"), llm)
    verdicts = {r.rule: r.verdict.value for r in result.report.results}

    assert verdicts["ON-PAY-01"] == "pass", result.facts.pay
    assert verdicts["ON-PAY-02"] == "pass", result.facts.pay
    assert verdicts["ON-VAC-01"] == "pass", result.facts.vacancy_statement
    assert verdicts["ON-CEX-01"] == "fail", result.facts.requirements
    assert all(p.parsers_agree for p in result.facts.pay if p.kind == "wage")


def test_live_refinement_rewrites_the_canadian_experience_sentence(llm: AnthropicLLM) -> None:
    ctx = Context(meets_headcount_threshold=True, uses_ai_in_hiring=False, existing_vacancy=True)
    pack = load_pack("CA-ON")
    base = inspect(POSTING, ctx, date(2026, 10, 19), pack, llm)
    refined = refine(base, ctx, date(2026, 10, 19), pack, llm)

    cex = [p for p in refined.patches if p.rule == "ON-CEX-01"]
    assert cex and all(p.verified for p in cex), refined.dropped
    print(f"\nRewrite: {cex[0].before!r} -> {cex[0].after!r}")  # noqa: T201
    assert "Canadian" not in (cex[0].after or "")
    assert {r.rule: r.verdict.value for r in refined.report.results}["ON-CEX-01"] == "pass"


def test_live_employer_size_search(llm: AnthropicLLM) -> None:
    from decimal import Decimal as D

    from app.compliance.employer import decide, look_up
    from app.compliance.llm import SEARCH_SETTINGS

    size = look_up("Shopify", "Ottawa, ON", llm, SEARCH_SETTINGS)
    assert size is not None, "the search call failed"
    print(f"\nFound: {size.model_dump()}")  # noqa: T201
    found = decide("Shopify", size, D(25))
    print(f"Decision: {found.model_dump()}")  # noqa: T201
    assert size.found and found.meets_threshold and found.basis == "search"


# Law-review sample (docs/law-review-2026-10.md): the wording the classifier must get right.
# "either" accepts both labels where the lawyer hasn't settled the reading yet.
CEX_SAMPLE = [
    ("3 years of Canadian accounting experience required.", {"violation"}),
    ("Previous experience in Canada is required.", {"violation"}),
    ("Must have worked in Canada for at least two years.", {"violation"}),
    ("Local work experience is required.", {"violation"}),
    ("Canadian work experience preferred.", {"violation", "borderline"}),
    ("Canadian experience is an asset.", {"violation", "borderline"}),
    ("Ontario payroll experience is an asset.", {"borderline", "violation"}),
    ("North American experience is required.", {"borderline", "violation"}),
    ("Bachelor's degree from a Canadian university.", {"violation"}),
    ("An established network of clients in Canada.", {"violation"}),
    ("Knowledge of Canadian tax legislation.", {"borderline", "ok"}),
    ("Legally entitled to work in Canada.", {"ok"}),
    ("P.Eng. licence required.", {"ok"}),
    ("Registered with the College of Nurses of Ontario.", {"ok"}),
    ("CPA designation is an asset.", {"ok"}),
    ("5+ years of payroll experience.", {"ok"}),
    ("Fluent in English; French is an asset.", {"ok"}),
    ("This role is based in Mississauga, Ontario (hybrid).", {"ok"}),
]
AI_SAMPLE = [
    ("We use AI tools to screen applications.", {"uses_ai"}),
    ("Screening is AI-assisted.", {"uses_ai"}),
    ("Applications are ranked with the help of artificial intelligence.", {"uses_ai"}),
    ("We use machine learning to shortlist candidates.", {"uses_ai"}),
    ("Applications are first screened by an automated system.", {"none"}),
    ("Our applicant tracking system (ATS) sorts applications automatically.", {"none"}),
    ("We do not use AI to screen, assess or select applicants.", {"no_ai"}),
    ("Experience with AI tools such as ChatGPT is an asset.", {"none"}),
]
VACANCY_SAMPLE = [
    ("This posting is for an existing vacancy.", {"existing"}),
    ("This role is currently open.", {"existing"}),
    ("There is no existing vacancy; we are building a talent pool for future openings.", {"not_existing"}),
    ("We may hire for this role in the future.", {"vague"}),
    ("We accept applications for this role on an ongoing basis.", {"vague"}),
    ("Apply by November 30.", {"none"}),
]


def test_live_law_review_classifier_sample(llm: AnthropicLLM) -> None:
    from app.compliance.classification import classify
    from app.compliance.llm import ModelSettings
    from app.compliance.normalise import normalise

    samples = [("canadian_experience", CEX_SAMPLE), ("ai", AI_SAMPLE), ("vacancy", VACANCY_SAMPLE)]
    lines = [text for _, sample in samples for text, _ in sample]
    doc = normalise("\n".join(lines))
    assert [s.text for s in doc.sentences] == lines, "every line must be one sentence"
    ids = {s.text: s.id for s in doc.sentences}
    wanted = {task: [ids[text] for text, _ in sample] for task, sample in samples}
    result = classify(doc, wanted, load_pack("CA-ON"), llm, ModelSettings())

    right, rows = 0, []
    for task, sample in samples:
        got = {label.sentence: label for label in getattr(result, task)}
        for text, accepted in sample:
            label = got[ids[text]]
            ok = label.label in accepted
            right += ok
            rows.append(f"{'ok ' if ok else 'XX '} {task:20} {label.label:12} {text}  ({label.reason})")
    total = sum(len(sample) for _, sample in samples)
    print(f"\n{right}/{total} labels accepted\n" + "\n".join(rows))  # noqa: T201
    assert right >= total * 0.85, "\n".join(rows)


LAW_REVIEW_POSTINGS = {
    "vague pay and preferred Canadian experience": (
        "Accounts Payable Clerk\nToronto, ON\n\nWhat you bring:\n- 3 years of accounts payable experience\n"
        "- Canadian work experience preferred\n- Legally entitled to work in Canada\n\nCompensation\n"
        "Competitive salary, DOE.\n\nApplications are first screened by an automated system.\n"
        "This posting is for an existing vacancy.\n",
        {"ON-APPL-02": "pass", "ON-PAY-01": "fail", "ON-VAC-01": "pass", "ON-AI-01": "pass"},
    ),
    "hourly range near the cap, remote across Canada": (
        "Customer Support Specialist\nRemote (Canada)\n\nAbout the role\nYou'll answer tickets and calls.\n\n"
        "Requirements\n- 2 years of support experience\n- Fluent in English\n\nPay\n$25 - $48 per hour.\n\n"
        "We are building a talent pool for this role; there is no existing vacancy.\n",
        {"ON-APPL-02": "needs_input", "ON-PAY-01": "pass", "ON-PAY-02": "needs_input", "ON-VAC-01": "pass", "ON-CEX-01": "pass"},
    ),
    "commission only, AI-assisted screening": (
        "Sales Representative\nOttawa, ON\n\nWhat we offer\nCommission only: $40,000 to $90,000 a year in expected "
        "commission.\n\nRequirements\n- North American sales experience\n- Valid driver's licence\n\n"
        "Screening is AI-assisted.\nThis role is currently open.\n",
        {"ON-APPL-02": "pass", "ON-PAY-01": "pass", "ON-AI-01": "warning"},  # the employer below says it doesn't use AI
    ),
    "exempt pay, Canadian degree, Ontario registration": (
        "Director of Nursing\nLondon, Ontario\n\nSalary: $150,000 - $250,000 per year.\n\nRequirements\n"
        "- Registered with the College of Nurses of Ontario\n- Degree from a Canadian university\n"
        "- 10 years of nursing leadership experience\n\nThis posting is for an existing vacancy.\n",
        {"ON-APPL-02": "pass", "ON-PAY-01": "not_applicable", "ON-PAY-02": "not_applicable", "ON-CEX-01": "fail"},
    ),
}


@pytest.mark.parametrize("name", list(LAW_REVIEW_POSTINGS))
def test_live_law_review_postings(llm: AnthropicLLM, name: str) -> None:
    text, expected = LAW_REVIEW_POSTINGS[name]
    ctx = Context(meets_headcount_threshold=True, uses_ai_in_hiring=False)
    result = inspect(text, ctx, date(2026, 10, 19), load_pack("CA-ON"), llm)
    verdicts = {r.rule: r.verdict.value for r in result.report.results}
    labels = {result.document.sentences[i].text: (v.cex, v.ai, v.vacancy) for i, v in result.labels.items()}
    gate = {k: getattr(result.extraction, k) for k in ("specific_position", "internal_only", "work_in_ontario", "locations")}
    print(f"\n{name}\n  verdicts: {verdicts}\n  gate: {gate}\n  pay: {[p.model_dump() for p in result.facts.pay]}\n  labels: {labels}")  # noqa: T201
    wrong = {rule: (verdicts.get(rule), want) for rule, want in expected.items() if verdicts.get(rule) != want}
    assert not wrong, wrong
