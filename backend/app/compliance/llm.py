"""Schema-bound LLM calls (Technical Design §7).

Every call returns a validated Pydantic object or raises LLMError: one retry, then fail closed.
Settings follow section 7: pinned model, no sampling parameters (Haiku 5.5 and Sonnet 5.5 reject them),
thinking off, explicit effort, no tools.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol, TypeVar

import anthropic
import pydantic

T = TypeVar("T", bound=pydantic.BaseModel)


class LLMError(Exception):
    """The model gave no valid structured answer after one retry, refused, or the API failed."""


@dataclass(frozen=True)
class ModelSettings:
    model: str = "claude-haiku-5-5"
    effort: str = "medium"
    max_tokens: int = 8000
    # Thinking off: Haiku 5.5 takes "disabled" (effort high or below); Sonnet 5.5 takes "between_tools".
    thinking: dict[str, Any] = field(default_factory=lambda: {"type": "disabled"})
    # Server-side refusal fallback (beta); Haiku 5.5 has none, so only Sonnet calls turn it on.
    fallbacks: bool = False


# Sentence rewrites (Technical Design §13, recommended setup).
REWRITE_SETTINGS = ModelSettings(
    model="claude-sonnet-5-5", max_tokens=2000, thinking={"type": "between_tools"}, fallbacks=True
)


# Employer-size lookups (inspector.py): Haiku 5.5 with the basic web search tool. Thinking stays on at low
# effort because with thinking off and a JSON format the model can skip a tool call it needs.
SEARCH_SETTINGS = ModelSettings(max_tokens=4000, effort="low", thinking={"type": "adaptive"})


class StructuredLLM(Protocol):
    def parse(
        self, *, system: str, user: str, schema: type[T], settings: ModelSettings, tools: list[dict[str, Any]] | None = None
    ) -> T: ...


# USD per million input / output tokens (Technical Design §13). Unknown models are priced as Sonnet.
PRICES_PER_MTOK = {
    "claude-haiku-5-5": (Decimal("0.10"), Decimal("0.50")),
    "claude-sonnet-5-5": (Decimal("2"), Decimal("10")),
}
WEB_SEARCH_USD = Decimal("0.01")  # $10 per 1,000 searches, on top of the result tokens


@dataclass
class SpendMeter:
    """Adds up what the calls of one request cost, from the token counts the API reports."""

    usd: Decimal = Decimal(0)

    def add(self, model: str, input_tokens: int, output_tokens: int, searches: int = 0) -> None:
        price_in, price_out = PRICES_PER_MTOK.get(model, PRICES_PER_MTOK["claude-sonnet-5-5"])
        self.usd += (price_in * input_tokens + price_out * output_tokens) / Decimal(1_000_000)
        self.usd += WEB_SEARCH_USD * searches


class AnthropicLLM:
    def __init__(self, client: anthropic.Anthropic | None = None, meter: SpendMeter | None = None) -> None:
        self.client = client or anthropic.Anthropic()
        self.meter = meter

    def parse(
        self, *, system: str, user: str, schema: type[T], settings: ModelSettings, tools: list[dict[str, Any]] | None = None
    ) -> T:
        problem = "no attempt made"
        for _ in range(2):
            request: dict[str, Any] = {
                "model": settings.model,
                "max_tokens": settings.max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
                "thinking": settings.thinking,
                "output_config": {"effort": settings.effort},
                "output_format": schema,
            }
            if tools:  # server tools only (web search); results are untrusted data like the posting
                request["tools"] = tools
            try:
                if settings.fallbacks:
                    response = self.client.beta.messages.parse(
                        **request, betas=["server-side-fallback-2026-07-01"], fallbacks="default"
                    )
                else:
                    response = self.client.messages.parse(**request)
            except (pydantic.ValidationError, ValueError) as error:
                problem = f"output failed the schema: {error}"
                continue
            except anthropic.APIError as error:  # the SDK has already retried 429s and 5xx
                raise LLMError(f"API error: {error}") from error
            usage = getattr(response, "usage", None)
            if self.meter is not None and usage is not None:
                server = getattr(usage, "server_tool_use", None)
                searches = (getattr(server, "web_search_requests", None) or 0) if server else 0
                model = getattr(response, "model", None) or settings.model
                self.meter.add(model, usage.input_tokens, usage.output_tokens, searches)
            if response.stop_reason == "refusal":
                raise LLMError("the model declined the request")
            if response.stop_reason == "max_tokens":
                problem = "output was cut off at max_tokens"
                continue
            if response.stop_reason == "pause_turn":  # the server's tool loop ran out of iterations
                problem = "the search did not finish"
                continue
            if response.parsed_output is None:
                problem = "no structured output in the response"
                continue
            return response.parsed_output
        raise LLMError(problem)
