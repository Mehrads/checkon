"""Load a rule pack from YAML and select the rules in force on a posting date (Technical Design §6, §10)."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict

RULEPACKS_DIR = Path(__file__).resolve().parents[2] / "rulepacks"


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    jurisdiction: str
    version: str
    kind: Literal["applicability", "content", "process"]
    effective_from: date
    effective_to: date | None = None  # last day in force
    citation: str
    source_url: str
    check: str | None
    params: dict[str, Any] = {}
    interpretation: bool
    reviewed_by: str | None = None
    reviewed_on: date | None = None
    fix: dict[str, str] | None = None
    messages: dict[str, str] = {}
    questions: dict[str, str] = {}
    examples: list[dict[str, str]] = []  # labelled sentences for the classifier prompt
    tests: list[str] = []

    def in_force(self, on: date) -> bool:
        return self.effective_from <= on and (self.effective_to is None or on <= self.effective_to)


class RulePack(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    jurisdiction: str
    version: str
    messages: dict[str, str] = {}
    rules: list[Rule]

    @property
    def label(self) -> str:
        return f"{self.jurisdiction}@{self.version}"

    def in_force(self, on: date) -> list[Rule]:
        return [rule for rule in self.rules if rule.in_force(on)]


def _to_decimal(value: Any) -> Any:
    """YAML numbers become Decimal so money arithmetic stays exact."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: _to_decimal(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_decimal(item) for item in value]
    return value


def load_pack(jurisdiction: str, directory: Path = RULEPACKS_DIR) -> RulePack:
    raw = yaml.safe_load((directory / jurisdiction / "rules.yaml").read_text(encoding="utf-8"))
    shared = raw.get("params", {})
    rules = [
        {
            **rule,
            "jurisdiction": raw["jurisdiction"],
            "params": _to_decimal({**shared, **rule.get("params", {})}),
        }
        for rule in raw["rules"]
    ]
    return RulePack(
        jurisdiction=raw["jurisdiction"],
        version=str(raw["version"]),
        messages=raw.get("messages", {}),
        rules=rules,
    )
