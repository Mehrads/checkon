"""Pay suggestions with a scripted LLM (no network): the occupation the model names, the Job Bank figures for the
region, current postings read by the money parser, the yearly cap, and the guardrails."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from app.compliance.checks import annualise
from app.compliance.llm import SEARCH_SETTINGS, Cited, LLMError
from app.compliance.models import PayUnit
from app.compliance.rulepack import load_pack
from app.pay.jobbank import JobBank
from app.pay.suggest import (
    BLOCKED_SITES,
    ConfirmedBand,
    OccupationMatch,
    PayRange,
    PostingSearch,
    Suggestion,
    age_in_days,
    postings_from,
    suggest,
)
from tests.compliance.fake_llm import FakeLLM
from tests.pay.fixtures import write_job_bank

PARAMS = next(r for r in load_pack("CA-ON").rules if r.id == "ON-PAY-02").params
TODAY = date(2026, 10, 22)
POSTING = "Payroll Specialist\nMississauga, ON (hybrid)\n\nYou'll run payroll for 400 employees."
RANDSTAD = "https://www.randstad.ca/jobs/payroll-specialist_mississauga_47139745/"
ROBERT_HALF = "https://www.roberthalf.com/ca/en/job/mississauga-on/payroll-specialist/05010"


class MemoryPostings:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], PostingSearch] = {}

    def get(self, key: tuple[str, str]) -> PostingSearch | None:
        return self.items.get(key)

    def put(self, key: tuple[str, str], value: PostingSearch) -> None:
        self.items[key] = value


@pytest.fixture
def bank(tmp_path: Path) -> JobBank:
    return write_job_bank(tmp_path / "data")


def quote(text: str, url: str = RANDSTAD, cited_text: str = "") -> dict[str, Any]:
    return {"text": text, "url": url, "title": "Payroll Specialist", "cited_text": cited_text}


def searched(*quotes: dict[str, Any], ages: dict[str, str] | None = None) -> dict[str, Any]:
    urls = {q["url"] for q in quotes}
    return {"quotes": list(quotes), "results": [{"url": u, "title": "t", "page_age": (ages or {}).get(u)} for u in urls]}


def match(code: str = "13102", confidence: str = "high", alternative: str | None = "13100") -> dict[str, Any]:
    return {"code": code, "confidence": confidence, "alternative": alternative}


def run(llm: FakeLLM, bank: JobBank, **changes: Any) -> Suggestion:
    args: dict[str, Any] = {
        "title": "Payroll Specialist", "location": "Mississauga, ON (hybrid)", "posting": POSTING,
        "hours": Decimal(40), "params": PARAMS, "band": None, "unit_hint": None, "noc": None, "job_bank": bank,
        "llm": llm, "today": TODAY, "search_settings": SEARCH_SETTINGS,
    }  # fmt: skip
    return suggest(**{**args, **changes})


def annual_width(found: PayRange, hours: Decimal = Decimal(40)) -> Decimal:
    return annualise(found.max - found.min, found.unit, hours, PARAMS)


# The occupation


def test_the_model_names_the_occupation_and_never_a_figure(bank: JobBank) -> None:
    llm = FakeLLM().queue(OccupationMatch, match()).queue(Cited, searched())
    found = run(llm, bank)

    assert found.status == "suggested"
    assert (found.occupation.code, found.occupation.title) == ("13102", "Payroll administrators")
    assert [o.code for o in found.alternatives] == ["13100"]
    [call] = llm.calls_for(OccupationMatch)
    assert "13102 Payroll administrators" in call.system and "{{OCCUPATIONS}}" not in call.system
    assert "<job_title>Payroll Specialist</job_title>" in call.user and "run payroll for 400 employees" in call.user
    assert call.tools is None and call.settings.model == "claude-haiku-5-5"
    assert set(OccupationMatch.model_fields) == {"code", "confidence", "alternative"}  # no field for pay


def test_low_confidence_asks_the_user_to_pick_one_of_two_occupations(bank: JobBank) -> None:
    llm = FakeLLM().queue(OccupationMatch, match(confidence="low"))
    pick = run(llm, bank)
    assert pick.status == "pick_occupation"
    assert [(o.code, o.title) for o in pick.alternatives] == [
        ("13102", "Payroll administrators"), ("13100", "Administrative officers"),
    ]  # fmt: skip
    assert pick.suggested is None and pick.sources == [] and llm.calls_for(Cited) == []  # nothing searched yet

    llm.queue(Cited, searched())
    picked = run(llm, bank, noc="13100")
    assert picked.status == "suggested" and picked.occupation.code == "13100"
    assert len(llm.calls_for(OccupationMatch)) == 1  # the user's pick needs no second mapping


def test_a_code_outside_noc_2021_fails_closed(bank: JobBank) -> None:
    with pytest.raises(LLMError):
        run(FakeLLM().queue(OccupationMatch, match(code="99999")), bank)
    with pytest.raises(ValueError):
        run(FakeLLM(), bank, noc="12345")


# Job Bank


def test_job_bank_figures_for_the_work_locations_region(bank: JobBank) -> None:
    toronto = run(FakeLLM().queue(OccupationMatch, match()).queue(Cited, searched()), bank, location="North York, ON")
    ottawa = run(FakeLLM().queue(OccupationMatch, match()).queue(Cited, searched()), bank, location="Kanata, ON")

    assert (toronto.region, toronto.market.median, toronto.market.unit) == ("Toronto", Decimal("31.25"), PayUnit.HOUR)
    assert (toronto.market.low, toronto.market.high, toronto.market.basis) == (Decimal(20), Decimal("46.96"), "job_bank")
    assert (ottawa.region, ottawa.market.median) == ("Ottawa", Decimal(32))
    [source] = [s for s in toronto.sources if s.kind == "job_bank"]
    assert source.name == "Job Bank wages: Payroll administrators (NOC 13102), Toronto"
    assert source.figures == "Low $20, median $31.25, high $46.96 an hour"
    assert source.url == "https://open.canada.ca/data/en/dataset/adad580f-76b0-4502-bd05-20c125de9116"
    assert source.date == "Published November 19, 2025, for 2023-2024 (Labour Force Survey)"
    assert source.licence == "Open Government Licence - Canada" and source.licence_url


def test_ontario_figures_when_the_region_has_none(bank: JobBank) -> None:
    found = run(FakeLLM().queue(Cited, searched()), bank, noc="00010", location="Thunder Bay, ON")
    assert found.region == "Northwest" and found.market.median == Decimal(80000) and found.market.unit == PayUnit.YEAR
    assert "Job Bank has no figures for this occupation in the Northwest region, so these are Ontario's." in found.notes


def test_figures_are_converted_to_the_postings_unit_at_its_hours(bank: JobBank) -> None:
    found = run(FakeLLM().queue(Cited, searched()), bank, noc="13102", location="Toronto", unit_hint=PayUnit.YEAR)
    assert (found.market.median, found.market.unit) == (Decimal("65000.00"), PayUnit.YEAR)  # 31.25 × 40 × 52
    assert "Hourly and yearly figures are compared at 40 hours a week." in found.notes


# The suggested range


def test_the_suggestion_is_centred_on_the_median_and_within_the_cap(bank: JobBank) -> None:
    found = run(FakeLLM().queue(Cited, searched()), bank, noc="13102", location="Toronto")
    assert found.suggested == PayRange(min=Decimal("23.00"), max=Decimal("39.50"), unit=PayUnit.HOUR)
    assert annual_width(found.suggested) <= 50000

    wide = run(FakeLLM().queue(Cited, searched()), bank, noc="21232", location="Toronto")  # quartiles $62,400 apart
    assert wide.suggested.unit == PayUnit.HOUR and annual_width(wide.suggested) <= 50000
    assert wide.suggested.max - wide.suggested.min == Decimal(24)  # the widest range in quarter dollars
    assert wide.suggested.min < Decimal("48.08") < wide.suggested.max

    shorter = run(FakeLLM().queue(Cited, searched()), bank, noc="21232", location="Toronto", hours=Decimal("37.5"))
    assert shorter.suggested.max - shorter.suggested.min == Decimal("25.50")  # $49,725 a year at 37.5 hours


def test_a_confirmed_band_comes_first_and_is_flagged_far_below_market(bank: JobBank) -> None:
    band = ConfirmedBand(
        title="Payroll Specialist", range=PayRange(min=Decimal(18), max=Decimal(20), unit=PayUnit.HOUR),
        confirmed_on=date(2026, 9, 1),
    )  # fmt: skip
    found = run(FakeLLM().queue(OccupationMatch, match()).queue(Cited, searched()), bank, band=band, location="Toronto")
    assert found.suggested == band.range and found.band == band.range
    assert found.flag == "below_market"  # 19 against a median of 31.25
    assert (found.sources[0].kind, found.sources[0].name) == ("band", "Your confirmed range for Payroll Specialist")
    assert found.sources[0].date == "Confirmed September 1, 2026"

    fair = band.model_copy(update={"range": PayRange(min=Decimal(29), max=Decimal(33), unit=PayUnit.HOUR)})
    assert run(FakeLLM().queue(Cited, searched()), bank, band=fair, noc="13102", location="Toronto").flag is None
    high = band.model_copy(update={"range": PayRange(min=Decimal(45), max=Decimal(50), unit=PayUnit.HOUR)})
    assert run(FakeLLM().queue(Cited, searched()), bank, band=high, noc="13102", location="Toronto").flag == "above_market"


def test_a_band_wider_than_the_cap_is_narrowed(bank: JobBank) -> None:
    band = ConfirmedBand(
        title="Payroll Specialist", range=PayRange(min=Decimal(50000), max=Decimal(120000), unit=PayUnit.YEAR),
        confirmed_on=date(2026, 9, 1),
    )  # fmt: skip
    found = run(FakeLLM().queue(Cited, searched()), bank, band=band, noc="13102", location="Toronto")
    assert found.suggested == PayRange(min=Decimal(60000), max=Decimal(110000), unit=PayUnit.YEAR)


def test_no_market_figures_means_no_suggested_range(bank: JobBank) -> None:
    found = run(FakeLLM().queue(Cited, searched()), bank, noc="99000")
    assert found.suggested is None and found.market is None
    assert "Job Bank publishes no wages for this occupation." in found.notes
    assert any("Enter the range you expect to pay" in note for note in found.notes)


# Current postings


def test_posting_pay_is_read_by_the_money_parser_from_the_quotes(bank: JobBank) -> None:
    answer = searched(
        quote("$25.00 - $27.00 per hour"),
        quote("28.5 - 33 CAD / Hourly", url=ROBERT_HALF),
        quote("about seventy thousand a year, or 70k"),  # no currency marker: not read
        quote("Salary: $80,000 -...", url="https://ca.jooble.org/jobs-payroll-specialist"),  # cut off mid-range
        quote("US$90,000 a year", url="https://jobs.example.com/payroll"),
        quote("$70,000–$80,000 a year", url="https://ca.indeed.com/viewjob?jk=1"),
        quote("$72,000–$78,000 a year", url="https://www.simplyhired.ca/search?q=payroll"),
        quote("$60,000–$65,000 a year", url="https://old.example.com/payroll"),
        ages={RANDSTAD: "105 days ago", "https://old.example.com/payroll": "867 days ago"},
    )
    llm = FakeLLM().queue(OccupationMatch, match()).queue(Cited, answer)
    found = run(llm, bank, location="Toronto")

    postings = [s for s in found.sources if s.kind == "posting"]
    assert [(s.url, s.figures, s.date) for s in postings] == [
        (RANDSTAD, "$25–$27 an hour", "Posted 105 days ago"),
        (ROBERT_HALF, "$28.50–$33 an hour", "Found October 22, 2026"),
    ]
    assert postings[0].quote == "$25.00 - $27.00 per hour" and postings[0].name == "randstad.ca"
    assert found.market.basis == "job_bank"  # Job Bank leads; the postings are listed beside it
    [search] = llm.calls_for(Cited)
    [tool] = search.tools
    assert (tool["type"], tool["max_uses"]) == ("web_search_20250305", 3)
    assert {"glassdoor.com", "linkedin.com", "indeed.com", "indeed.ca"} <= set(tool["blocked_domains"]) == set(BLOCKED_SITES)
    assert search.settings == SEARCH_SETTINGS  # the employer-size lookup's settings
    assert "<job_title>Payroll Specialist</job_title>" in search.user and "<location>Toronto</location>" in search.user


def test_postings_alone_give_the_market_range(bank: JobBank) -> None:
    answer = searched(
        quote("$65,000 - $72,000"), quote("$70,000–$80,000 a year", url=ROBERT_HALF),
        quote("$28 - $32 per hour", url="https://jobs.example.com/p"),
    )  # fmt: skip
    found = run(FakeLLM().queue(Cited, answer), bank, noc="99000")
    assert (found.market.basis, found.market.unit) == ("postings", PayUnit.YEAR)  # most postings are yearly
    assert (found.market.low, found.market.median, found.market.high) == (Decimal(58240), Decimal(68500), Decimal(80000))
    assert found.suggested.unit == PayUnit.YEAR and annual_width(found.suggested) <= 50000


def test_a_failed_search_still_suggests_from_job_bank(bank: JobBank) -> None:
    found = run(FakeLLM().queue(Cited, LLMError("API error")), bank, noc="13102", location="Toronto")
    assert found.suggested is not None and "We couldn't search current postings just now." in found.notes


def test_the_postings_search_is_kept_for_a_week(bank: JobBank) -> None:
    cache = MemoryPostings()
    llm = FakeLLM().queue(Cited, searched(quote("$25.00 - $27.00 per hour")))
    first = run(llm, bank, noc="13102", postings_cache=cache)
    again = run(llm, bank, noc="13102", location="Mississauga, Ontario", postings_cache=cache)
    assert len(llm.calls_for(Cited)) == 1 and first.sources == again.sources
    assert list(cache.items) == [("payroll specialist", "mississauga on")]


def test_postings_older_than_a_year_and_page_ages() -> None:
    assert age_in_days("105 days ago", TODAY) == 105
    assert age_in_days("a year ago", TODAY) == 365
    assert age_in_days("3 months ago", TODAY) == 90
    assert age_in_days("July 15, 2026", TODAY) == 99
    assert age_in_days("2024-01-02", TODAY) == 1024
    assert age_in_days("recently", TODAY) is None and age_in_days(None, TODAY) is None
    old = Cited.model_validate(searched(quote("$25 an hour", url="https://a.example"), ages={"https://a.example": "2 years ago"}))
    assert postings_from(old, TODAY) == []
