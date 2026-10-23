"""Langfuse traces carry metadata only (app/core/tracing.py): a whole check, through the real AnthropicLLM and the
real usage recorder, exports no posting text and no model answer, but does export each call's model, tokens and
cost and the request's verdicts."""

import json
import uuid
from collections.abc import Generator
from datetime import date
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.api.free_check import rate_limited
from app.api.routes.checks import (
    TraceDep,
    get_limits,
    get_llm,
    get_posting_date,
    get_sizes,
    get_usage,
)
from app.api.usage import PostgresUsage
from app.compliance.classification import Classification
from app.compliance.extraction import Extraction
from app.compliance.llm import AnthropicLLM, ModelSettings, SpendMeter
from app.compliance.refiner import _Rewrite
from app.core.config import settings
from app.core.tracing import langfuse_client, make_client
from app.main import app
from tests.compliance.fake_llm import FakeLLM
from tests.compliance.test_api import API, MemoryLimits
from tests.compliance.test_employer import MemorySizes
from tests.compliance.test_inspector import POSTING, extraction, labels

MARKER = "Zanzibar7731"  # in the posting's title and body, and in every answer the model gives
POSTED = POSTING.replace("Payroll Specialist", f"{MARKER} Payroll Specialist", 1).replace(
    "400 employees", f"400 employees at {MARKER}"
)


class FakeAnthropic:
    """The Anthropic client's shape over FakeLLM's queued answers, with token counts like the API's."""

    def __init__(self, fake: FakeLLM) -> None:
        self.fake = fake
        self.messages = self
        self.beta = SimpleNamespace(messages=self)

    def parse(self, *, system: str, messages: list[dict[str, Any]], output_format: type, model: str, **_: Any) -> Any:
        answer = self.fake.parse(
            system=system, user=messages[0]["content"], schema=output_format, settings=ModelSettings(model=model)
        )
        usage = SimpleNamespace(
            input_tokens=1000, output_tokens=200, cache_read_input_tokens=0, cache_creation_input_tokens=0
        )
        return SimpleNamespace(parsed_output=answer, stop_reason="end_turn", model=model, usage=usage)


class NoDatabase:
    def add(self, _: Any) -> None: ...
    def commit(self) -> None: ...


@pytest.fixture
def exported() -> Generator[InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    # Langfuse keeps one exporter per public key, so each test needs its own key
    client = make_client(f"pk-lf-{uuid.uuid4()}", "sk-lf-test", "http://localhost:9", exporter=exporter)
    fake = FakeLLM()
    fake.queue(Extraction, extraction(title=f"{MARKER} Payroll Specialist"))
    fake.queue(Classification, labels(vacancy=[{"sentence": 8, "label": "existing", "reason": MARKER}]))
    fake.queue(_Rewrite, {"sentence": "2+ years of payroll experience"})
    fake.queue(Classification, {"canadian_experience": [{"sentence": 4, "label": "ok", "reason": MARKER}], "vacancy": [], "ai": []})  # fmt: skip

    def llm(trace: TraceDep) -> AnthropicLLM:
        return AnthropicLLM(FakeAnthropic(fake), meter=SpendMeter(), trace=trace)  # type: ignore[arg-type]

    def usage(trace: TraceDep) -> PostgresUsage:
        return PostgresUsage(NoDatabase(), trace)  # type: ignore[arg-type]

    app.dependency_overrides.update({
        langfuse_client: lambda: client, get_llm: llm, get_usage: usage, get_posting_date: lambda: date(2026, 10, 19),
        get_limits: lambda: MemoryLimits(per_week=100), get_sizes: MemorySizes, rate_limited: lambda: None,
    })  # fmt: skip
    yield exporter
    app.dependency_overrides.clear()
    client.shutdown()


def everything(span: ReadableSpan) -> str:
    """All a span would send: its name, attributes, events and resource."""
    return json.dumps(
        [span.name, dict(span.attributes or {}), [(e.name, dict(e.attributes or {})) for e in span.events],
         dict(span.resource.attributes)],
        default=str,
    )  # fmt: skip


def run_a_check(client: TestClient) -> None:
    check = client.post(f"{API}/inspect", json={"text": POSTED, "meets_headcount_threshold": True})
    assert check.status_code == 200, check.text
    check_id = check.json()["check_id"]
    assert client.post(f"{API}/refine", json={"check_id": check_id}).status_code == 200
    answers = {"check_id": check_id, "answers": {"uses_ai_in_hiring": False}}
    assert client.post(f"{API}/answers", json=answers).status_code == 200
    accepted = client.post(f"{API}/patches/accept", json={"check_id": check_id, "decisions": []})
    assert accepted.status_code == 200
    assert MARKER in accepted.json()["text"]  # the marker really went through the check


def test_no_posting_text_or_model_answer_is_exported(exported: InMemorySpanExporter) -> None:
    run_a_check(TestClient(app))
    spans = exported.get_finished_spans()
    assert spans
    for span in spans:
        sent = everything(span)
        assert MARKER not in sent
        assert "Canadian payroll experience" not in sent and "60,000" not in sent
        assert not any(key.endswith((".input", ".output")) for key in span.attributes or {})


def test_calls_and_requests_are_traced(exported: InMemorySpanExporter) -> None:
    run_a_check(TestClient(app))
    spans = {span.name: span for span in exported.get_finished_spans()}
    assert {"inspect_posting", "refine_posting", "answer_questions", "accept_patches"} <= set(spans)

    extraction_call = everything(spans["Extraction"])
    assert "claude-haiku-5-5" in extraction_call and '\\"input_tokens\\": 1000' in extraction_call
    assert "claude-sonnet-5-5" in everything(spans["Rewrite"])
    inspected = everything(spans["inspect_posting"])
    assert "not_compliant" in inspected and "ON-CEX-01" in inspected and "check_id" in inspected
    assert "visitor" not in inspected


def test_placeholder_keys_leave_tracing_off() -> None:
    assert not settings.model_copy(update={"LANGFUSE_PUBLIC_KEY": None, "LANGFUSE_SECRET_KEY": None}).tracing_enabled
    placeholder = {"LANGFUSE_PUBLIC_KEY": "replace-me", "LANGFUSE_SECRET_KEY": "replace-me"}
    assert not settings.model_copy(update=placeholder).tracing_enabled
    keys = {"LANGFUSE_PUBLIC_KEY": "pk-lf-1", "LANGFUSE_SECRET_KEY": "sk-lf-1"}
    assert settings.model_copy(update=keys).tracing_enabled
