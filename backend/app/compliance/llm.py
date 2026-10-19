"""Schema-bound LLM calls (Technical Design §7).

Every call returns a validated Pydantic object or raises LLMError: one retry, then fail closed.
Settings follow section 7: pinned model, no sampling parameters (Haiku 5.5 and Sonnet 5.5 reject them),
thinking off, explicit effort, no tools.
"""

from dataclasses import dataclass
from typing import Protocol, TypeVar

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


class StructuredLLM(Protocol):
    def parse(self, *, system: str, user: str, schema: type[T], settings: ModelSettings) -> T: ...


class AnthropicLLM:
    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        self.client = client or anthropic.Anthropic()

    def parse(self, *, system: str, user: str, schema: type[T], settings: ModelSettings) -> T:
        problem = "no attempt made"
        for _ in range(2):
            try:
                response = self.client.messages.parse(
                    model=settings.model,
                    max_tokens=settings.max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    # Haiku 5.5 accepts disabled thinking at effort high or below.
                    thinking={"type": "disabled"},
                    output_config={"effort": settings.effort},
                    output_format=schema,
                )
            except (pydantic.ValidationError, ValueError) as error:
                problem = f"output failed the schema: {error}"
                continue
            except anthropic.APIError as error:  # the SDK has already retried 429s and 5xx
                raise LLMError(f"API error: {error}") from error
            if response.stop_reason == "refusal":
                raise LLMError("the model declined the request")
            if response.stop_reason == "max_tokens":
                problem = "output was cut off at max_tokens"
                continue
            if response.parsed_output is None:
                problem = "no structured output in the response"
                continue
            return response.parsed_output
        raise LLMError(problem)
