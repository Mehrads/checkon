"""Langfuse traces of each request's model calls (Technical Design §12), metadata only.

CheckON doesn't keep posting text (the privacy page), so a trace never holds a prompt, a posting or a model's
answer. It holds the request's route, kind, status, plan, check id and rule verdicts, and for each model call its
step, model, tokens, cost, latency and stop reason. Nothing here sets an observation's input or output, the client
has its own OpenTelemetry provider and exports only Langfuse's own spans (another library's spans could carry a
prompt), and tests/api/routes/test_tracing.py fails if a marker in the posting reaches an exported span.

Off unless settings.tracing_enabled.
"""

from decimal import Decimal
from functools import cache
from typing import Any

from langfuse import Langfuse, LangfuseGeneration, LangfuseSpan, is_langfuse_span
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SpanExporter

from app.core.config import settings


def make_client(public_key: str, secret_key: str, base_url: str, exporter: SpanExporter | None = None) -> Langfuse:
    return Langfuse(
        public_key=public_key, secret_key=secret_key, base_url=base_url,
        environment="development" if settings.FASTAPI_ENV == "development" else "production",
        tracer_provider=TracerProvider(), should_export_span=is_langfuse_span, span_exporter=exporter,
    )  # fmt: skip


@cache
def langfuse_client() -> Langfuse | None:
    if not settings.tracing_enabled:
        return None
    assert settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY
    return make_client(settings.LANGFUSE_PUBLIC_KEY, settings.LANGFUSE_SECRET_KEY, settings.LANGFUSE_BASE_URL)


class ModelCall:
    """One model call's generation; does nothing when tracing is off."""

    def __init__(self, generation: LangfuseGeneration | None) -> None:
        self._generation = generation

    def finish(self, *, model: str, usage: dict[str, int], usd: Decimal, stop_reason: str | None) -> None:
        if self._generation is not None:
            self._generation.update(
                model=model, usage_details=usage, cost_details={"total": float(usd)},
                metadata={"stop_reason": stop_reason},
            )  # fmt: skip
            self._generation.end()

    def fail(self, error: str) -> None:
        if self._generation is not None:
            self._generation.update(level="ERROR", status_message=error)
            self._generation.end()


class RequestTrace:
    """One API request: a span named after its route, a generation per model call, and the request's facts as
    the span's metadata when it ends. Does nothing when tracing is off."""

    def __init__(self, client: Langfuse | None, name: str) -> None:
        self._client = client
        self._root: LangfuseSpan | None = client.start_observation(name=name) if client else None
        self._facts: dict[str, Any] = {}

    def note(self, **facts: Any) -> None:
        """Adds ids, statuses, counts and amounts about the request. Never words from a posting."""
        self._facts.update({key: value for key, value in facts.items() if value is not None})

    def start(self, step: str, model: str) -> ModelCall:
        if self._root is None:
            return ModelCall(None)
        return ModelCall(self._root.start_observation(name=step, as_type="generation", model=model))

    def end(self) -> None:
        if self._root is None or self._client is None:
            return
        self._root.update(metadata=self._facts)
        self._root.end()
        # Cloud Run throttles the CPU between requests, so the background exporter can't be relied on. This runs
        # after the response is sent (get_trace's request scope), so the visitor doesn't wait for it.
        self._client.flush()
