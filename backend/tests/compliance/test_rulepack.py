"""The rule pack is well formed: every check resolves, every test file exists, every rule is tested."""

import yaml

from app.compliance.checks import CHECKS
from app.compliance.rulepack import RULEPACKS_DIR, load_pack

PACK = load_pack("CA-ON")
PACK_DIR = RULEPACKS_DIR / "CA-ON"


def test_pack_label() -> None:
    assert PACK.label == "CA-ON@1.0.0"


def test_checked_rules_resolve_to_a_check() -> None:
    for rule in PACK.rules:
        if rule.kind == "process":
            assert rule.check is None, rule.id
        else:
            assert rule.check in CHECKS, rule.id


def test_listed_test_files_exist() -> None:
    for rule in PACK.rules:
        for test in rule.tests:
            assert (PACK_DIR / test).is_file(), f"{rule.id}: {test}"


def test_every_checked_rule_is_covered_by_its_test_file() -> None:
    for rule in PACK.rules:
        if rule.check is None:
            continue
        assert rule.tests, f"{rule.id} lists no test files"
        covered = any(
            rule.id in case["expect"]
            for test in rule.tests
            for case in yaml.safe_load((PACK_DIR / test).read_text(encoding="utf-8"))["cases"]
        )
        assert covered, f"{rule.id} has no case in {rule.tests}"


def test_interpretation_rules_are_not_signed_off_yet() -> None:
    # Flip this once the lawyer's review is recorded in the rule records (Technical Design §8, layer 3).
    unsigned = [rule.id for rule in PACK.rules if rule.interpretation and rule.reviewed_by is None]
    assert unsigned == ["ON-PAY-01", "ON-PAY-02", "ON-VAC-01", "ON-AI-01", "ON-CEX-01"]
