"""The rule pack is well formed: every check resolves, every test file exists, every rule is tested."""

import yaml

from app.compliance.checks import CHECKS
from app.compliance.rulepack import RULEPACKS_DIR, load_pack

PACK = load_pack("CA-ON")
PACK_DIR = RULEPACKS_DIR / "CA-ON"


def test_pack_label() -> None:
    assert PACK.label == "CA-ON@1.3.0"


def test_every_rule_cites_a_section() -> None:
    """Citations name the section (law review, docs/law-review-2026-10.md), not just the Part."""
    for rule in PACK.rules:
        assert "s. " in rule.citation, f"{rule.id}: {rule.citation}"
        assert rule.source_url.startswith("https://www.ontario.ca/laws/"), rule.id


def test_classifier_examples_use_the_labels_the_classifier_accepts() -> None:
    from app.compliance.classification import TASKS, AILabel, CexLabel, VacancyLabel

    schemas = {"canadian_experience": CexLabel, "vacancy": VacancyLabel, "ai": AILabel}
    for task, rule_id in TASKS.items():
        rule = next(rule for rule in PACK.rules if rule.id == rule_id)
        allowed = set(schemas[task].model_fields["label"].annotation.__args__)
        assert rule.examples, rule_id
        for example in rule.examples:
            assert example["label"] in allowed, f"{rule_id}: {example}"
            assert example["text"] and example["reason"], f"{rule_id}: {example}"


def test_form_blocks_resolve_and_use_the_form_classifier_labels() -> None:
    """Only s. 8.3 (1) names the application form, so only ON-CEX-01 runs on it."""
    from app.compliance.form import FormLabel

    allowed = set(FormLabel.model_fields["label"].annotation.__args__)
    with_form = [rule for rule in PACK.rules if rule.form]
    assert [rule.id for rule in with_form] == ["ON-CEX-01"]
    for rule in with_form:
        assert rule.form.check in CHECKS and {"pass", "fail", "warning", "optional"} <= set(rule.form.messages)
        assert rule.form.examples
        for example in rule.form.examples:
            assert example["label"] in allowed and example["text"] and example["reason"], example


def test_checked_rules_resolve_to_a_check() -> None:
    for rule in PACK.rules:
        if rule.kind == "process":
            assert rule.check is None, rule.id
        else:
            assert rule.check in CHECKS, rule.id


def test_process_rules_and_only_they_carry_a_reminder() -> None:
    for rule in PACK.rules:
        if rule.kind == "process":
            assert rule.reminder, rule.id
        else:
            assert rule.reminder is None, rule.id


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
