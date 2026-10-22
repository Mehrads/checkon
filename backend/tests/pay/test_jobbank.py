"""Job Bank wages: the shipped Ontario files, the region of a job location, and the lookup by region."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.compliance.models import PayUnit
from app.pay.jobbank import ONTARIO, JobBank, load_job_bank
from tests.pay.fixtures import write_job_bank


@pytest.fixture
def bank(tmp_path: Path) -> JobBank:
    return write_job_bank(tmp_path / "data")


def test_the_shipped_files_are_ontarios_job_bank_wages() -> None:
    real = load_job_bank()
    assert real.dataset.licence == "Open Government Licence - Canada"
    assert real.dataset.url.startswith("https://open.canada.ca/")
    assert real.dataset.published >= date(2025, 11, 19)
    assert len(real.occupations) == 516  # NOC 2021 unit groups
    assert real.regions[ONTARIO] == "Ontario" and len(real.regions) == 12
    assert {region for _, region in real.wages} <= set(real.regions)
    assert set(real.places.values()) <= set(real.regions)
    assert {noc for noc, _ in real.wages} <= set(real.occupations)
    for wage in real.wages.values():  # Job Bank's low and high are the 10th and 90th percentiles
        figures = [value for value in (wage.low, wage.median, wage.high) if value is not None]
        assert figures == sorted(figures)
    # Job Bank places Burlington in Hamilton–Niagara Peninsula, though its census division is in Toronto's region
    assert real.regions[real.region_for("Burlington, ON")] == "Hamilton–Niagara Peninsula"
    assert real.regions[real.region_for("Scarborough, Ontario")] == "Toronto"
    assert real.regions[real.region_for("Greater Sudbury")] == "Northeast"


@pytest.mark.parametrize(
    ("location", "region"),
    [
        ("Toronto, ON", "ER3530"),
        ("North York, Toronto, ON (hybrid)", "ER3530"),
        ("Kanata (Ottawa), Ontario", "ER3510"),
        ("Orléans, Ottawa, ON", "ER3510"),
        ("123 King Street West, Toronto, ON", "ER3530"),  # a whole part that is a place wins over King Township
        ("Thunder Bay ON", "ER3595"),
        ("Remote (Canada)", ONTARIO),
        ("Ontario", ONTARIO),
        (None, ONTARIO),
    ],
)
def test_a_job_location_is_placed_in_its_economic_region(bank: JobBank, location: str | None, region: str) -> None:
    assert bank.region_for(location) == region


def test_wages_by_occupation_and_region(bank: JobBank) -> None:
    toronto, ottawa = bank.wage("13102", "ER3530"), bank.wage("13102", "ER3510")
    assert toronto and ottawa
    assert (toronto.low, toronto.median, toronto.high, toronto.unit) == (
        Decimal(20), Decimal("31.25"), Decimal("46.96"), PayUnit.HOUR,
    )  # fmt: skip
    assert ottawa.median == Decimal(32)


def test_a_region_without_figures_falls_back_to_ontario(bank: JobBank) -> None:
    northwest = bank.wage("00010", "ER3595")  # published, but without figures
    assert northwest and northwest.region == ONTARIO and northwest.unit == PayUnit.YEAR
    assert bank.wage("13102", "ER3595").region == ONTARIO  # not published for the region at all
    assert bank.wage("99000", "ER3530") is None
