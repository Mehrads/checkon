"""AnthropicLLM request settings and fail-closed handling, against a stand-in client."""

from types import SimpleNamespace
from typing import Any

import pydantic
import pytest

from app.compliance.llm import AnthropicLLM, LLMError, ModelSettings


class Answer(pydantic.BaseModel):
    label: str


class FakeMessages:
    def __init__(self, *outcomes: Any) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[dict[str, Any]] = []

    def parse(self, **request: Any) -> Any:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def response(stop_reason: str = "end_turn", parsed: Any = None) -> SimpleNamespace:
    return SimpleNamespace(stop_reason=stop_reason, parsed_output=parsed)


def llm_with(*outcomes: Any) -> tuple[AnthropicLLM, FakeMessages]:
    messages = FakeMessages(*outcomes)
    return AnthropicLLM(client=SimpleNamespace(messages=messages)), messages


def call(llm: AnthropicLLM) -> Answer:
    return llm.parse(system="sys", user="text", schema=Answer, settings=ModelSettings())


def test_request_uses_the_section_7_settings() -> None:
    llm, messages = llm_with(response(parsed=Answer(label="ok")))
    assert call(llm).label == "ok"
    request = messages.requests[0]
    assert request["model"] == "claude-haiku-5-5"
    assert request["thinking"] == {"type": "disabled"}
    assert request["output_config"] == {"effort": "medium"}
    assert request["output_format"] is Answer
    assert "temperature" not in request and "top_p" not in request and "tools" not in request


def test_schema_failure_is_retried_once() -> None:
    error = pydantic.ValidationError.from_exception_data("Answer", [])
    llm, messages = llm_with(error, response(parsed=Answer(label="ok")))
    assert call(llm).label == "ok"
    assert len(messages.requests) == 2


def test_two_cut_off_answers_fail_closed() -> None:
    llm, _ = llm_with(response("max_tokens"), response("max_tokens"))
    with pytest.raises(LLMError, match="max_tokens"):
        call(llm)


def test_refusal_fails_closed_without_retry() -> None:
    llm, messages = llm_with(response("refusal"))
    with pytest.raises(LLMError, match="declined"):
        call(llm)
    assert len(messages.requests) == 1


def test_meter_prices_reported_tokens() -> None:
    from decimal import Decimal

    from app.compliance.llm import SpendMeter

    usage = SimpleNamespace(input_tokens=6100, output_tokens=1500)
    messages = FakeMessages(SimpleNamespace(stop_reason="end_turn", parsed_output=Answer(label="ok"), usage=usage,
                                            model="claude-haiku-5-5"))  # fmt: skip
    meter = SpendMeter()
    llm = AnthropicLLM(client=SimpleNamespace(messages=messages), meter=meter)
    call(llm)
    assert meter.usd == Decimal("0.00136")  # 6,100 x $0.10/M + 1,500 x $0.50/M
    meter.add("claude-sonnet-5-5", 1500, 150)
    assert meter.usd == Decimal("0.00136") + Decimal("0.0045")
