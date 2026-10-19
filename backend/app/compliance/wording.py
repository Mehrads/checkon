"""The approved wording library (Technical Design §5): fixed statements the Refiner inserts."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict

from app.compliance.rulepack import RULEPACKS_DIR

Variant = Literal["formal", "plain"]


class Entry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rule: str
    labels: dict[str, str]
    variants: dict[Variant, str]


class WordingLibrary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str
    reviewed_by: str | None = None
    reviewed_on: str | None = None
    entries: dict[str, Entry]

    def text(self, key: str, variant: Variant = "formal") -> str:
        return self.entries[key].variants[variant]

    @property
    def placeholder(self) -> str:
        return self.text("pay_placeholder")

    def labels_for(self, sentence: str) -> dict[str, str] | None:
        """The declared labels when the sentence is library wording, else None."""
        for entry in self.entries.values():
            if sentence in entry.variants.values():
                return entry.labels
        return None


def load_wording(jurisdiction: str, directory: Path = RULEPACKS_DIR) -> WordingLibrary:
    raw = yaml.safe_load((directory / jurisdiction / "wording.yaml").read_text(encoding="utf-8"))
    return WordingLibrary(**{**raw, "version": str(raw["version"])})
