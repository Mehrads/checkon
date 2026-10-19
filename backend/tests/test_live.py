"""One real inspection against the Claude API. Skipped unless RUN_LIVE_LLM=1; costs well under a cent.

Run it with:  RUN_LIVE_LLM=1 ANTHROPIC_API_KEY=... uv run pytest tests/test_live.py -v
"""

import os
from datetime import date

import pytest

from app.compliance.inspector import inspect
from app.compliance.llm import AnthropicLLM
from app.compliance.models import Context
from app.compliance.rulepack import load_pack
from tests.test_inspector import POSTING

pytestmark = pytest.mark.skipif(os.environ.get("RUN_LIVE_LLM") != "1", reason="set RUN_LIVE_LLM=1 to call the API")


def test_live_inspection_of_the_sample_posting() -> None:
    ctx = Context(meets_headcount_threshold=True, uses_ai_in_hiring=False)
    result = inspect(POSTING, ctx, date(2026, 10, 19), load_pack("CA-ON"), AnthropicLLM())
    verdicts = {r.rule: r.verdict.value for r in result.report.results}

    assert verdicts["ON-PAY-01"] == "pass"
    assert verdicts["ON-PAY-02"] == "pass"
    assert verdicts["ON-VAC-01"] == "pass"
    assert verdicts["ON-CEX-01"] == "fail"
    assert all(p.parsers_agree for p in result.facts.pay if p.kind == "wage")
