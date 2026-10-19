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
