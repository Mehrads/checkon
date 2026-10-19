"""Money parser: amounts, k, ranges, open ends, periods and spans."""

from decimal import Decimal

import pytest

from app.compliance.models import PayUnit
from app.compliance.money import parse_pay

H, W, M, Y = PayUnit.HOUR, PayUnit.WEEK, PayUnit.MONTH, PayUnit.YEAR


@pytest.mark.parametrize(
    ("text", "low", "high", "unit", "stated"),
    [
        # Yearly ranges
        ("$60,000 - $80,000 per year", 60000, 80000, Y, True),
        ("$60,000–$80,000", 60000, 80000, Y, False),
        ("$60,000 to $80,000 annually", 60000, 80000, Y, True),
        ("between $60,000 and $80,000 a year", 60000, 80000, Y, True),
        ("$100,000 - $150,000 CAD per year", 100000, 150000, Y, True),
        ("CAD 60,000 - 80,000 per annum", 60000, 80000, Y, True),
        ("Annual salary: $70,000", 70000, 70000, Y, True),
        ("$60,000.00 - $80,000.00/yr", 60000, 80000, Y, True),
        # k
        ("$60k-80k", 60000, 80000, Y, False),
        ("$60-80K", 60000, 80000, Y, False),
        ("$60k - 80", 60000, 80000, Y, False),
        ("$62.5k", 62500, 62500, Y, False),
        # Hourly
        ("$28.50 - $34.00 per hour", Decimal("28.50"), 34, H, True),
        ("$25/hr", 25, 25, H, True),
        ("$25 an hour", 25, 25, H, True),
        ("$25 hourly", 25, 25, H, True),
        ("$25/hour to $30/hour", 25, 30, H, True),
        ("Hourly rate: $25 - $30", 25, 30, H, True),
        ("$28-$34", 28, 34, H, False),
        # Monthly and weekly
        ("$5,000 - $6,000 per month", 5000, 6000, M, True),
        ("$5,000-$6,000/month", 5000, 6000, M, True),
        ("$5,000 - $6,000 monthly", 5000, 6000, M, True),
        ("$1,200 per week", 1200, 1200, W, True),
        # Open ends
        ("$70,000+", 70000, None, Y, False),
        ("$70k+ per year", 70000, None, Y, True),
        ("$70,000 and up", 70000, None, Y, False),
        ("starting at $60,000", 60000, None, Y, False),
        ("up to $90,000", None, 90000, Y, False),
        ("Up to $45/hour", None, 45, H, True),
        # Other currencies and markers
        ("C$60,000", 60000, 60000, Y, False),
        ("75,000 dollars a year", 75000, 75000, Y, True),
    ],
)
def test_reads_one_amount(text: str, low, high, unit: PayUnit, stated: bool) -> None:
    [reading] = parse_pay(text)
    assert reading.min == (None if low is None else Decimal(low))
    assert reading.max == (None if high is None else Decimal(high))
    assert reading.unit == unit
    assert reading.unit_stated is stated


@pytest.mark.parametrize(
    "text",
    [
        "3-5 years of experience",
        "401(k) matching",
        "40 hours per week",
        "Call 416-555-1234",
        "Posted 2026-01-01",
        "A $5M revenue business",
        "$2 million in annual sales",
    ],
)
def test_ignores_numbers_that_are_not_pay(text: str) -> None:
    assert parse_pay(text) == []


def test_plus_bonus_is_not_open_ended() -> None:
    [reading] = parse_pay("$70,000 + bonus")
    assert (reading.min, reading.max) == (70000, 70000)


def test_range_plus_bonus_keeps_the_range() -> None:
    [reading] = parse_pay("$60,000-$80,000 + bonus")
    assert (reading.min, reading.max) == (60000, 80000)


def test_currency() -> None:
    assert parse_pay("$80,000")[0].currency == "CAD"
    assert parse_pay("US$80,000")[0].currency == "USD"
    assert parse_pay("80,000 USD")[0].currency == "USD"


def test_middle_amount_has_no_known_period() -> None:
    [reading] = parse_pay("$4,500")
    assert reading.unit is None
    assert reading.unit_stated is False


def test_working_hours_before_the_amount_do_not_set_the_period() -> None:
    [reading] = parse_pay("Full-time, 40 hours per week, $25 - $30")
    assert reading.unit == H
    assert reading.unit_stated is False


def test_hourly_beats_salary_before_the_amount() -> None:
    [reading] = parse_pay("Hourly salary: $25")
    assert reading.unit == H


def test_spans_cover_qualifiers_and_periods() -> None:
    text = "Salary: $60,000 - $80,000 per year. Bonus up to $5,000. Overtime from $40/hour."
    readings = parse_pay(text)
    assert [r.text for r in readings] == ["$60,000 - $80,000 per year", "up to $5,000", "from $40/hour"]
    for reading in readings:
        assert text[reading.span[0] : reading.span[1]] == reading.text


def test_amount_followed_by_comma() -> None:
    [reading] = parse_pay("$60,000, plus benefits")
    assert (reading.min, reading.max) == (60000, 60000)


def test_reversed_pair_is_not_a_range() -> None:
    readings = parse_pay("$80,000 - $60,000")
    assert [(r.min, r.max) for r in readings] == [(80000, 80000), (60000, 60000)]
