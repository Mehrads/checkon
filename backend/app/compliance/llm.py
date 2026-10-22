"""Schema-bound LLM calls (Technical Design §7).

Every call returns a validated Pydantic object or raises LLMError: one retry, then fail closed.
Settings follow section 7: pinned model, no sampling parameters (Haiku 5.5 and Sonnet 5.5 reject them),
thinking off, explicit effort, no tools.

The one exception is a cited web search (`cite`, for pay suggestions): structured output can't carry the
search's citations, so it returns the model's cited sentences with the link and page text each one cites.
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


class Quote(pydantic.BaseModel):
    """A sentence of the model's answer and the search result it cites."""

    text: str  # the model's words
    url: str  # the cited result's address, as the search returned it
    title: str | None = None
    cited_text: str = ""  # the result's own text, quoted by the API (at most about 150 characters)


class SearchResult(pydantic.BaseModel):
    url: str
    title: str | None = None
    page_age: str | None = None  # as the search reports it: "105 days ago", "July 15, 2026"


class Cited(pydantic.BaseModel):
    quotes: list[Quote] = []
    results: list[SearchResult] = []  # every result the searches returned


class CitingLLM(Protocol):
    def cite(self, *, system: str, user: str, settings: ModelSettings, tools: list[dict[str, Any]]) -> Cited: ...


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

    def _count(self, response: Any, settings: ModelSettings) -> None:
        usage = getattr(response, "usage", None)
        if self.meter is not None and usage is not None:
            server = getattr(usage, "server_tool_use", None)
            searches = (getattr(server, "web_search_requests", None) or 0) if server else 0
            model = getattr(response, "model", None) or settings.model
            self.meter.add(model, usage.input_tokens, usage.output_tokens, searches)

    def cite(self, *, system: str, user: str, settings: ModelSettings, tools: list[dict[str, Any]]) -> Cited:
        """One search request, not retried: a second run would search, and cost, again. An answer cut off by
        max_tokens or the server's tool loop keeps the sentences it had cited."""
        try:
            response = self.client.messages.create(  # type: ignore[call-overload]  # settings hold plain dicts
                model=settings.model, max_tokens=settings.max_tokens, system=system,
                messages=[{"role": "user", "content": user}], thinking=settings.thinking,
                output_config={"effort": settings.effort}, tools=tools,
            )  # fmt: skip
        except anthropic.APIError as error:
            raise LLMError(f"API error: {error}") from error
        self._count(response, settings)
        if response.stop_reason == "refusal":
            raise LLMError("the model declined the request")
        cited = Cited()
        for block in response.content:
            if block.type == "web_search_tool_result" and isinstance(block.content, list):  # else a search error
                cited.results += [
                    SearchResult(url=r.url, title=r.title, page_age=getattr(r, "page_age", None)) for r in block.content
                ]
            elif block.type == "text":
                for citation in block.citations or []:
                    if citation.type == "web_search_result_location":
                        cited.quotes.append(Quote(
                            text=block.text, url=citation.url, title=citation.title, cited_text=citation.cited_text or "",
                        ))  # fmt: skip
                        break
        return cited

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
            self._count(response, settings)
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
