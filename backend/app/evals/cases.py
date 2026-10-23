"""Golden-set cases: one YAML file per posting in backend/evals/golden/<slice>/<id>.yaml (backend/evals/README.md).

Labels are the verdict a careful reader gives each rule from the posting and the case's context, agreed by two
labellers (disagreements go to the lawyer). A case with no labels yet is collected but not scored.
"""

import re
from datetime import date
from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.compliance.inspector import REFUSALS
from app.compliance.models import Context, Verdict

GOLDEN_DIR = Path(__file__).resolve().parents[2] / "evals" / "golden"
Slice = Literal["real", "synthetic", "out_of_scope", "adversarial"]
SLICES: tuple[Slice, ...] = ("real", "synthetic", "out_of_scope", "adversarial")
TARGETS: dict[Slice, int] = {"real": 150, "synthetic": 100, "out_of_scope": 25, "adversarial": 25}  # 04-V1-Scope §3
RULES = ("ON-APPL-01", "ON-APPL-02", "ON-PAY-01", "ON-PAY-02", "ON-VAC-01", "ON-AI-01", "ON-CEX-01")
DEFAULT_POSTED = date(2026, 10, 1)
_ID = re.compile(r"[a-z0-9][a-z0-9-]*")


class Source(BaseModel):
    """Where a real posting was read: a public job board or careers page (PRD §7)."""

    model_config = ConfigDict(extra="forbid")

    url: str
    board: str | None = None  # greenhouse, lever, ashby, smartrecruiters or page
    employer: str | None = None
    location: str | None = None  # as the board shows it
    fetched: date


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    slice: Slice
    purpose: str = ""  # synthetic and adversarial cases: what the case tests
    source: Source | None = None  # real postings
    variant_of: str | None = None  # adversarial cases: the case it was made from
    posted: date = DEFAULT_POSTED  # the day the rules are checked for
    # The answers an employer would give for this posting (Context fields). Headcount defaults to 25 or more, so
    # no employer-size search runs; out-of-scope cases set it when the size is the point.
    context: dict[str, Any] = {}
    text: str
    labels: dict[str, Verdict] = {}  # per rule in RULES; empty until labelled
    refusal: str | None = None  # instead of labels: the input should be refused for this reason (REFUSALS)
    labelled_by: list[str] = []
    notes: str = ""

    @field_validator("id")
    @classmethod
    def _id(cls, value: str) -> str:
        if not _ID.fullmatch(value):
            raise ValueError("ids are lowercase letters, digits and hyphens")
        return value

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        unknown = set(self.labels) - set(RULES)
        if unknown:
            raise ValueError(f"labels for unknown rules: {sorted(unknown)}")
        if self.refusal is not None and (self.refusal not in REFUSALS or self.labels):
            raise ValueError("refusal must be one of the Inspector's reasons, and replaces the labels")
        if self.slice == "real" and self.source is None:
            raise ValueError("a real posting needs its source")
        if self.slice == "adversarial" and not self.variant_of:
            raise ValueError("an adversarial case names the case it was made from (variant_of)")
        self.ctx()  # the context must be valid Context fields
        return self

    @property
    def labelled(self) -> bool:
        return bool(self.labels) or self.refusal is not None

    def ctx(self) -> Context:
        return Context.model_validate({"meets_headcount_threshold": True, **self.context})


def load_case(path: Path) -> Case:
    case = Case.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    if path.stem != case.id or path.parent.name != case.slice:
        raise ValueError(f"{path}: a case lives at <slice>/<id>.yaml (found id {case.id!r}, slice {case.slice!r})")
    return case


def load_cases(root: Path = GOLDEN_DIR) -> list[Case]:
    cases = [load_case(path) for name in SLICES for path in sorted((root / name).glob("*.yaml"))]
    ids = [case.id for case in cases]
    if duplicates := sorted({i for i in ids if ids.count(i) > 1}):
        raise ValueError(f"duplicate case ids: {duplicates}")
    known = set(ids)
    if missing := sorted({c.variant_of for c in cases if c.variant_of and c.variant_of not in known}):
        raise ValueError(f"variant_of names cases that don't exist: {missing}")
    return cases


class _Block(str):
    """A string YAML writes as a literal block, so a posting reads as it does on the page."""


class _Dumper(yaml.SafeDumper):  # type: ignore[misc]
    pass


_Dumper.add_representer(_Block, lambda dumper, data: dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|"))


def dump_case(case: Case) -> str:
    data = case.model_dump(mode="json", exclude_defaults=True)
    data = {"id": case.id, "slice": case.slice, **data}  # always first, even at their defaults
    # Literal blocks can't hold trailing spaces or tabs, so they go
    data["text"] = _Block("\n".join(line.rstrip() for line in case.text.replace("\t", "    ").splitlines()) + "\n")
    data.setdefault("labels", {})
    return str(yaml.dump(data, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=120))


def write_case(case: Case, root: Path = GOLDEN_DIR) -> Path:
    path = root / case.slice / f"{case.id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_case(case), encoding="utf-8")
    return path
