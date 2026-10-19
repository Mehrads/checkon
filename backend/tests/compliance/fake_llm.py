"""A scripted stand-in for the LLM: returns queued answers per schema and records every call."""

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from app.compliance.llm import ModelSettings


@dataclass
class Call:
    system: str
    user: str
    schema: type


@dataclass
class FakeLLM:
    answers: dict[type, list[Any]] = field(default_factory=dict)
    calls: list[Call] = field(default_factory=list)

    def queue(self, schema: type[BaseModel], *answers: Any) -> "FakeLLM":
        self.answers.setdefault(schema, []).extend(answers)
        return self

    def parse(self, *, system: str, user: str, schema: type, settings: ModelSettings) -> Any:
        self.calls.append(Call(system, user, schema))
        queue = self.answers.get(schema, [])
        if not queue:
            raise AssertionError(f"no answer queued for {schema.__name__}")
        answer = queue.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer if isinstance(answer, schema) else schema.model_validate(answer)

    def calls_for(self, schema: type) -> list[Call]:
        return [call for call in self.calls if call.schema is schema]
