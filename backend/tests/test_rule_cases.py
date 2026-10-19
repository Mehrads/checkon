"""Layer 1 rule tests (Technical Design §8): table-driven cases stored with the rule pack."""

from typing import Any

import pytest
import yaml

from app.compliance.engine import evaluate
from app.compliance.models import Context, Facts
from app.compliance.rulepack import RULEPACKS_DIR, load_pack

PACK = load_pack("CA-ON")
CASES_DIR = RULEPACKS_DIR / "CA-ON" / "tests"
DEFAULTS = yaml.safe_load((CASES_DIR / "defaults.yaml").read_text(encoding="utf-8"))


def _merge(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "posting_date": case.get("posting_date", DEFAULTS["posting_date"]),
        "facts": {**DEFAULTS["facts"], **case.get("facts", {})},
        "context": {**DEFAULTS["context"], **case.get("context", {})},
        "expect": case["expect"],
    }


def load_cases() -> list[Any]:
    params = []
    for path in sorted(CASES_DIR.glob("*.yaml")):
        if path.name == "defaults.yaml":
            continue
        for case in yaml.safe_load(path.read_text(encoding="utf-8"))["cases"]:
            params.append(pytest.param(_merge(case), id=f"{path.stem}: {case['name']}"))
    return params


@pytest.mark.parametrize("case", load_cases())
def test_rule_case(case: dict[str, Any]) -> None:
    facts = Facts.model_validate(case["facts"])
    ctx = Context.model_validate(case["context"])
    report = evaluate(facts, ctx, PACK, case["posting_date"])

    expect = dict(case["expect"])
    if "status" in expect:
        assert report.status == expect.pop("status"), report.message
    results = {result.rule: result for result in report.results}
    for rule, verdict in expect.items():
        assert rule in results, f"{rule} missing from the report"
        assert results[rule].verdict == verdict, f"{rule}: {results[rule].message}"
