"""Employer size from a web search: the decision in code, and the lookup inside the Inspector."""

from datetime import date
from decimal import Decimal

import pytest

from app.compliance.classification import Classification
from app.compliance.employer import EmployerSize, SizeCache, decide, look_up
from app.compliance.extraction import Extraction
from app.compliance.inspector import inspect
from app.compliance.llm import SEARCH_SETTINGS, LLMError
from app.compliance.models import Context
from app.compliance.rulepack import load_pack
from tests.compliance.fake_llm import FakeLLM
from tests.compliance.test_inspector import POSTING, extraction, labels

PACK = load_pack("CA-ON")
TEXT = POSTING + "\nMaple Leaf Payroll Ltd. is an equal opportunity employer.\n"
EMPLOYER = "Maple Leaf Payroll Ltd."
NOT_ASKED = Context(uses_ai_in_hiring=False)  # the free check never asks about headcount


def size(**figures) -> EmployerSize:
    base = {"found": True, "total_employees_min": None, "total_employees_max": None, "ontario_employees_min": None,
            "ontario_employees_max": None, "summary": "about 2,000 employees worldwide", "source_url": "https://www.mapleleaf.example/about"}  # fmt: skip
    return EmployerSize(**{**base, **figures})


class MemorySizes:
    """The employer-size cache without Postgres."""

    def __init__(self) -> None:
        self.items: dict[tuple[str, str], EmployerSize] = {}

    def get(self, key: tuple[str, str]) -> EmployerSize | None:
        return self.items.get(key)

    def put(self, key: tuple[str, str], value: EmployerSize) -> None:
        self.items[key] = value


# The decision


@pytest.mark.parametrize(
    ("figures", "meets", "basis"),
    [
        ({"total_employees_min": 2000, "total_employees_max": 2000}, True, "search"),
        ({"total_employees_min": 51, "total_employees_max": 200}, True, "search"),
        ({"total_employees_min": 5000, "ontario_employees_min": 10, "ontario_employees_max": 15}, False, "search"),
        ({"total_employees_min": 5, "total_employees_max": 12}, False, "search"),
        ({"total_employees_min": 11, "total_employees_max": 50}, True, "assumed"),  # straddles 25
        ({}, True, "assumed"),  # found the company, but no figures
        ({"found": False}, True, "assumed"),
    ],
)
def test_decision_from_the_figures(figures: dict, meets: bool, basis: str) -> None:
    found = decide(EMPLOYER, size(**figures), Decimal(25))
    assert (found.meets_threshold, found.basis) == (meets, basis)


def test_evidence_names_the_employer_and_the_source_domain() -> None:
    found = decide(EMPLOYER, size(total_employees_min=2000, total_employees_max=2000), Decimal(25))
    assert found.evidence == "Maple Leaf Payroll Ltd.: about 2,000 employees worldwide (mapleleaf.example)"


def test_no_employer_name_means_assumed() -> None:
    assert decide(None, None, Decimal(25)).basis == "assumed"


# Inside the Inspector


def run(llm: FakeLLM, ctx: Context = NOT_ASKED, employer: str | None = EMPLOYER, sizes: SizeCache | None = None):
    llm.queue(Extraction, extraction(employer=employer)).queue(Classification, labels())
    return inspect(TEXT, ctx, date(2026, 10, 19), PACK, llm, sizes=sizes)


def appl(result) -> tuple[str, str]:
    rule = next(r for r in result.report.results if r.rule == "ON-APPL-01")
    return rule.verdict.value, rule.message


def test_named_employer_is_searched_and_the_finding_is_shown() -> None:
    llm = FakeLLM().queue(EmployerSize, size(total_employees_min=2000, total_employees_max=2000))
    result = run(llm)
    [search] = llm.calls_for(EmployerSize)
    assert search.tools and search.tools[0]["type"] == "web_search_20250305"
    assert "<employer>Maple Leaf Payroll Ltd.</employer>" in search.user
    verdict, message = appl(result)
    assert verdict == "pass"
    assert message.startswith("Maple Leaf Payroll Ltd.: about 2,000 employees worldwide (mapleleaf.example).")
    assert result.context.headcount_basis == "search"


def test_small_employer_found_by_search_is_not_covered() -> None:
    llm = FakeLLM().queue(EmployerSize, size(total_employees_min=8, total_employees_max=8, summary="8 employees"))
    result = run(llm)
    assert appl(result)[0] == "not_applicable"
    assert result.report.status == "not_applicable"


def test_unnamed_employer_is_not_searched_and_rules_are_assumed() -> None:
    llm = FakeLLM()
    result = run(llm, employer=None)
    assert llm.calls_for(EmployerSize) == []
    verdict, message = appl(result)
    assert verdict == "pass" and message.startswith("We couldn't confirm the employer's size")


def test_failed_search_assumes_the_rules_apply() -> None:
    llm = FakeLLM().queue(EmployerSize, LLMError("the search did not finish"))
    result = run(llm)
    assert appl(result)[0] == "pass"
    assert result.context.headcount_basis == "assumed"


def test_the_same_employer_is_searched_once() -> None:
    llm, sizes = FakeLLM().queue(EmployerSize, size(total_employees_min=2000, total_employees_max=2000)), MemorySizes()
    first, second = run(llm, sizes=sizes), run(llm, sizes=sizes)
    assert len(llm.calls_for(EmployerSize)) == 1
    assert appl(second) == appl(first)
    assert second.context.headcount_basis == "search"


def test_the_cache_holds_the_figures_by_employer_and_location() -> None:
    found = size(total_employees_min=2000, total_employees_max=2000)
    sizes = MemorySizes()
    run(FakeLLM().queue(EmployerSize, found), sizes=sizes)
    assert sizes.items == {("maple leaf payroll ltd.", "mississauga, on"): found}


def test_the_cache_key_ignores_case_and_spacing() -> None:
    llm, sizes = FakeLLM().queue(EmployerSize, size()), MemorySizes()
    look_up("Maple Leaf Payroll Ltd.", "Mississauga, ON", llm, SEARCH_SETTINGS, sizes)
    look_up("maple leaf  PAYROLL Ltd.", "MISSISSAUGA, ON", llm, SEARCH_SETTINGS, sizes)
    assert len(llm.calls_for(EmployerSize)) == 1


def test_another_location_is_searched_again() -> None:
    llm, sizes = FakeLLM().queue(EmployerSize, size(), size(), size()), MemorySizes()
    look_up(EMPLOYER, "Mississauga, ON", llm, SEARCH_SETTINGS, sizes)
    look_up(EMPLOYER, "Ottawa, ON", llm, SEARCH_SETTINGS, sizes)
    look_up(EMPLOYER, None, llm, SEARCH_SETTINGS, sizes)
    assert len(llm.calls_for(EmployerSize)) == 3
    assert {location for _, location in sizes.items} == {"mississauga, on", "ottawa, on", ""}


def test_a_failed_search_is_not_cached() -> None:
    llm, sizes = FakeLLM().queue(EmployerSize, LLMError("the search did not finish"), size()), MemorySizes()
    assert look_up(EMPLOYER, None, llm, SEARCH_SETTINGS, sizes) is None
    assert sizes.items == {}
    assert look_up(EMPLOYER, None, llm, SEARCH_SETTINGS, sizes) == size()
    assert len(llm.calls_for(EmployerSize)) == 2


def test_without_a_cache_every_check_searches() -> None:
    llm = FakeLLM().queue(EmployerSize, size(), size())
    run(llm)
    run(llm)
    assert len(llm.calls_for(EmployerSize)) == 2


def test_a_given_headcount_skips_the_search() -> None:
    llm = FakeLLM()
    run(llm, ctx=Context(meets_headcount_threshold=True, uses_ai_in_hiring=False))
    assert llm.calls_for(EmployerSize) == []
