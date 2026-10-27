"""The golden set's files, its runner's scoring and the collector, with a scripted LLM and no network."""

from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.audit.boards import Board, Found
from app.compliance.classification import Classification
from app.compliance.extraction import Extraction
from app.evals import collect as collector
from app.evals.cases import RULES, SLICES, Case, load_case, load_cases, write_case
from app.compliance.models import Question
from app.compliance.refiner import OPEN_ENDED, Dropped, Patch, Refinement
from app.evals.golden import Result, Run, added_facts, run_case, score, waits_on_employer
from tests.compliance.fake_llm import FakeLLM
from tests.compliance.test_inspector import PACK, POSTING, extraction, labels

ALL_PASS = dict.fromkeys(RULES, "pass")


def case(**changes: Any) -> Case:
    base: dict[str, Any] = {
        "id": "syn-test-01", "slice": "synthetic", "text": POSTING, "context": {"uses_ai_in_hiring": False},
        "labels": ALL_PASS | {"ON-CEX-01": "fail"}, "labelled_by": ["first", "second"],
    }  # fmt: skip
    return Case.model_validate(base | changes)


def result(c: Case, *runs: Mapping[str, str]) -> Result:
    return Result(c, [Run(verdicts={rule: str(v) for rule, v in run.items()}) for run in runs])


def gates(results: list[Result]) -> dict[str, tuple[str, str]]:
    return {gate.name.split(" (")[0]: (gate.value, gate.outcome) for gate in score(results).gates}


# The files


def test_every_case_in_the_repo_loads() -> None:
    cases = load_cases()
    assert {c.slice for c in cases} <= set(SLICES)


def test_a_case_round_trips_through_yaml(tmp_path: Path) -> None:
    path = write_case(case(), tmp_path)
    assert path == tmp_path / "synthetic" / "syn-test-01.yaml"
    assert "text: |\n  Payroll Specialist\n" in path.read_text()
    assert load_case(path) == case()


def test_a_case_lives_at_its_slice_and_id(tmp_path: Path) -> None:
    path = write_case(case(), tmp_path)
    path.rename(tmp_path / "synthetic" / "other-name.yaml")
    with pytest.raises(ValueError, match="<slice>/<id>.yaml"):
        load_cases(tmp_path)


@pytest.mark.parametrize(
    "changes",
    [
        {"labels": {"ON-XYZ-01": "pass"}},  # no such rule
        {"labels": {"ON-PAY-01": "maybe"}},  # no such verdict
        {"refusal": "not_a_posting"},  # a refusal replaces the labels
        {"slice": "real"},  # a real posting needs its source
        {"slice": "adversarial"},  # an adversarial case names its original
        {"context": {"headcount_guess": 30}},  # not a Context field
        {"id": "Has Spaces"},
    ],
)
def test_invalid_cases_are_refused(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        case(**changes)


def test_variant_of_must_name_a_case(tmp_path: Path) -> None:
    write_case(case(id="adv-01", slice="adversarial", variant_of="syn-missing"), tmp_path)
    with pytest.raises(ValueError, match="syn-missing"):
        load_cases(tmp_path)


# Running a case


def test_a_case_runs_through_the_inspector() -> None:
    run = run_case(case(), PACK, FakeLLM().queue(Extraction, extraction()).queue(Classification, labels()))
    assert run.error is None and run.refused is None
    assert run.verdicts["ON-CEX-01"] == "fail" and run.verdicts["ON-PAY-01"] == "pass"


def test_refusals_and_errors_are_recorded_not_raised() -> None:
    refused = run_case(case(), PACK, FakeLLM().queue(Extraction, extraction(input_kind="not_a_posting")))
    assert refused.refused == "not_a_posting" and refused.verdict("ON-PAY-01") == "refused"
    failed = run_case(case(), PACK, FakeLLM())  # nothing queued
    assert failed.error and failed.error.startswith("AssertionError") and failed.verdict("ON-PAY-01") == "error"


def test_added_facts_flags_new_numbers_and_names_in_model_rewrites() -> None:
    from app.compliance.refiner import Patch

    def patch(after: str, writer: str = "llm") -> Patch:
        return Patch(id="p", rule="ON-CEX-01", op="replace", span=(0, 1), before="b", after=after, writer=writer)  # type: ignore[arg-type]

    source = "2+ years of Canadian payroll experience at Acme"
    assert added_facts(source, [patch("2+ years of payroll experience")]) == []
    assert added_facts(source, [patch("Payroll experience at Acme")]) == []  # first word and known names are fine
    assert len(added_facts(source, [patch("5+ years of payroll experience")])) == 1
    assert len(added_facts(source, [patch("2+ years of payroll experience with Ceridian")])) == 1
    assert added_facts(source, [patch("We use AI on 3 steps", writer="wording_library")]) == []


# Scoring


def test_recall_precision_and_consistency() -> None:
    found = case(id="found", labels=ALL_PASS | {"ON-PAY-01": "fail"})
    missed = case(id="missed", labels=ALL_PASS | {"ON-CEX-01": "fail"})
    false_fail = case(id="false-fail", labels=ALL_PASS)
    measured = gates([
        result(found, found.labels, found.labels, found.labels),
        result(missed, ALL_PASS, ALL_PASS, ALL_PASS),
        result(false_fail, ALL_PASS | {"ON-VAC-01": "fail"}, ALL_PASS, ALL_PASS),
    ])  # fmt: skip
    assert measured["Recall on violations: pay, vacancy and AI"] == ("100.0% (1/1)", "pass")
    assert measured["Recall on violations: Canadian experience"] == ("0.0% (0/1)", "fail")
    assert measured["Precision on fail, every rule"] == ("0.0% (0/1)", "fail")  # ON-VAC-01, the lowest
    assert measured["Same verdicts across 3 runs: code rules"] == ("100.0% (6/6)", "pass")
    assert measured["Same verdicts across 3 runs: overall"] == ("95.2% (20/21)", "fail")
    assert measured["Refiner: fixable failures fixed and verified"][1] == "not measured"  # no --refine
    assert measured["Golden set labelled by two people"] == ("1.0% (3/300)", "fail")


def test_only_people_count_as_labellers() -> None:
    drafted = case(labelled_by=["claude", "first"])
    assert gates([result(drafted, drafted.labels)])["Golden set labelled by two people"][0] == "0.0% (0/300)"


def test_injected_text_that_changes_a_verdict_fails_its_gate() -> None:
    original = case(id="orig")
    injected = case(id="adv-01", slice="adversarial", variant_of="orig")
    clean = gates([result(original, original.labels), result(injected, injected.labels)])
    assert clean["Verdict changes caused by injected text"] == ("0", "pass")
    swayed = gates([result(original, original.labels), result(injected, original.labels | {"ON-CEX-01": "pass"})])
    assert swayed["Verdict changes caused by injected text"] == ("1", "fail")


def test_refiner_gates_and_expected_refusals() -> None:
    fixed = case(id="fixed")
    run = Run(verdicts={**ALL_PASS, "ON-CEX-01": "fail"}, fixable=["ON-CEX-01"], fixed=["ON-CEX-01"])
    campaign = case(id="campaign", labels={}, refusal="not_a_posting")
    s = score([Result(fixed, [run]), result(campaign, ALL_PASS)])
    measured = {gate.name: (gate.value, gate.outcome) for gate in s.gates}
    assert measured["Refiner: fixable failures fixed and verified"] == ("100.0% (1/1)", "pass")
    assert measured["Refiner: rewrites that add a fact"] == ("0", "pass")
    assert s.refusals == [("campaign", "not_a_posting", "not refused")]


def test_failures_left_for_the_employer_are_not_counted_as_unfixed() -> None:
    pick = Patch(id="p1", rule="ON-PAY-02", op="replace", span=(0, 5), before="$1-$9", after=None,
                 options=["$1-$5"], writer="code", default=False)  # fmt: skip
    asked = Refinement.model_construct(patches=[pick], questions=[Question(id="existing_vacancy", text="?")], dropped=[])
    assert waits_on_employer(asked) == {"ON-PAY-02", "ON-VAC-01"}
    open_ended = Dropped(rule="ON-PAY-02", span=(0, 5), guidance="", failures=[OPEN_ENDED])
    unwritten = Dropped(rule="ON-CEX-01", span=(0, 5), guidance="", failures=["The rewrite call gave no usable sentence."])
    dropped = Refinement.model_construct(patches=[], questions=[], dropped=[open_ended, unwritten])
    assert waits_on_employer(dropped) == {"ON-PAY-02"}

    waiting = Run(verdicts={**ALL_PASS, "ON-VAC-01": "fail", "ON-CEX-01": "fail"}, fixable=["ON-CEX-01"],
                  fixed=["ON-CEX-01"], waiting=["ON-VAC-01"])  # fmt: skip
    s = score([Result(case(id="waiting"), [waiting])])
    measured = {gate.name: (gate.value, gate.outcome) for gate in s.gates}
    assert measured["Refiner: fixable failures fixed and verified"] == ("100.0% (1/1)", "pass")
    assert s.waiting == 1


def test_unlabelled_cases_are_counted_not_scored() -> None:
    unlabelled = case(labels={}, labelled_by=[])
    s = score([result(unlabelled, ALL_PASS)])
    assert s.counts["synthetic"] == {"cases": 1, "labelled": 0, "by_two": 0, "target": 100}
    assert all(rule["labelled"] == 0 for rule in s.rules.values())


# Collecting


def test_collect_keeps_ontario_postings_masks_contacts_and_skips_repeats(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    text = "Payroll Specialist\nToronto, ON\nQuestions: jo.smith@acme.ca or (416) 555-0199.\nSalary: $60,000 - $80,000"
    board = Board("greenhouse", "acme", "Acme", "https://boards.greenhouse.io/acme", [
        Found("1", "Payroll Specialist", "Toronto, ON", "https://boards.greenhouse.io/acme/jobs/1", "ontario", text=text),
        Found("2", "Clerk", "Calgary, AB", "https://boards.greenhouse.io/acme/jobs/2", "canada", text="Clerk\nCalgary"),
    ])  # fmt: skip
    monkeypatch.setattr(collector, "read_board", lambda *_: board)
    added = collector.collect(board.url, today=date(2026, 10, 23), root=tmp_path)
    assert [c.id for c in added] == ["greenhouse-acme-1"]
    saved = load_case(tmp_path / "real" / "greenhouse-acme-1.yaml")
    assert "Questions: [email] or [phone]." in saved.text and "$60,000 - $80,000" in saved.text
    assert saved.source and saved.source.employer == "Acme" and saved.posted == date(2026, 10, 23)
    assert not saved.labelled
    assert collector.collect(board.url, today=date(2026, 10, 23), root=tmp_path) == []  # already in the set
    outside = collector.collect(board.url, outside=True, today=date(2026, 10, 23), root=tmp_path)
    assert [c.slice for c in outside] == ["out_of_scope"]
