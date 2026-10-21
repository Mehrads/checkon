"""The admin Stats numbers, against Postgres (run `docker compose up -d db` and migrate first)."""

from collections.abc import Generator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.api.routes.stats import compute_stats
from app.core.config import settings
from app.models import (
    ContactMessage,
    CustomRequest,
    Feedback,
    FreeCheckSpend,
    UsageEvent,
)

API = settings.API_V1_STR
NOW = datetime(2026, 12, 9, 17, tzinfo=UTC)  # Wednesday noon in Toronto; the week starts Monday, December 7
TABLES = (UsageEvent, CustomRequest, ContactMessage, Feedback, FreeCheckSpend)


@pytest.fixture
def empty(db: Session) -> Generator[Session]:
    for table in TABLES:
        db.execute(delete(table))
    db.commit()
    yield db
    for table in TABLES:
        db.execute(delete(table))
    db.commit()


def at(day: int, month: int = 12, hour: int = 15) -> datetime:
    return datetime(2026, month, day, hour, tzinfo=UTC)


def test_weekly_numbers_returning_visitors_and_timing(empty: Session) -> None:
    empty.add_all([
        # Visitor a: first check 40 days ago, back 10 days later, and again this week.
        UsageEvent(kind="check", at=at(30, 10), visitor="a", check_id="a1", status="not_compliant"),
        UsageEvent(kind="check", at=at(9, 11), visitor="a", check_id="a2", status="compliant"),
        UsageEvent(kind="check", at=at(8), visitor="a", check_id="a3", status="not_compliant", duration_ms=10_000),
        UsageEvent(kind="refine", at=at(8), check_id="a3", status="ok", duration_ms=8_000),
        # Visitor b: first check 35 days ago; hitting the weekly limit an hour later isn't a return.
        UsageEvent(kind="check", at=at(4, 11), visitor="b", check_id="b1", status="compliant"),
        UsageEvent(kind="quota", at=at(4, 11, hour=16), visitor="b"),
        # Visitor c: new this week, applied two fixes.
        UsageEvent(kind="check", at=at(7), visitor="c", check_id="c1", status="not_compliant", duration_ms=4_000),
        UsageEvent(kind="refine", at=at(7), check_id="c1", status="ok", duration_ms=6_000),
        UsageEvent(kind="refine", at=at(7, hour=16), check_id="c1", status="ok", duration_ms=1_000),  # after answers
        UsageEvent(kind="accept", at=at(7), check_id="c1", count=2),
        # Visitor d pasted something that isn't a posting.
        UsageEvent(kind="refused", at=at(8), visitor="d", status="not_a_posting"),
        CustomRequest(created_at=at(8), hr_system="BambooHR", postings_per_month="10-50", wants="ATS", email="hr@example.com"),
        ContactMessage(created_at=at(1), name="Pat", email="pat@example.com", interest="starter", message="Hi"),
        ContactMessage(created_at=at(9, hour=14), name="Sam", email="sam@example.com", interest="custom", message="ATS"),
        Feedback(created_at=at(7), target_kind="check", target_id="check", rating="up"),
        Feedback(created_at=at(8), target_kind="finding", target_id="ON-CEX-01", rating="looks_wrong"),
        FreeCheckSpend(day=date(2026, 12, 8), usd=Decimal("0.01")),
        FreeCheckSpend(day=date(2026, 11, 30), usd=Decimal("0.02")),
    ])  # fmt: skip
    empty.commit()

    stats = compute_stats(empty, NOW)

    this_week, last_week = stats.weeks[0], stats.weeks[1]
    assert len(stats.weeks) == 12
    assert this_week.start == date(2026, 12, 7) and last_week.start == date(2026, 11, 30)
    assert (this_week.checks, this_week.visitors, this_week.new_visitors) == (2, 2, 1)
    assert (this_week.refused, this_week.limit_hits, this_week.fixes_applied) == (1, 0, 1)
    assert (this_week.custom_requests, this_week.plan_enquiries, this_week.contact_messages) == (2, 0, 1)
    assert (this_week.feedback_up, this_week.feedback_down) == (1, 1)
    assert this_week.model_spend_usd == Decimal("0.01")
    assert (last_week.plan_enquiries, last_week.model_spend_usd, last_week.checks) == (1, Decimal("0.02"), 0)

    assert (stats.totals.checks, stats.totals.visitors, stats.totals.fixes_applied) == (5, 3, 1)
    assert (stats.totals.custom_requests, stats.totals.plan_enquiries, stats.totals.contact_messages) == (2, 1, 2)
    assert stats.totals.model_spend_usd == Decimal("0.03")
    assert stats.totals.first_check == at(30, 10)

    assert (stats.returning.cohort, stats.returning.returned, stats.returning.rate) == (2, 1, 0.5)

    # Findings 4 s and 10 s; fixes add the first rewrite only: 10 s and 18 s.
    assert (stats.timing.checks, stats.timing.findings_p50, stats.timing.findings_p95) == (2, 4.0, 10.0)
    assert (stats.timing.fixes_p50, stats.timing.fixes_p95) == (10.0, 18.0)


def test_no_usage_yet(empty: Session) -> None:
    stats = compute_stats(empty, NOW)
    assert stats.totals.checks == 0 and stats.totals.first_check is None
    assert stats.returning.rate is None
    assert stats.timing.findings_p95 is None


def test_only_superusers_see_stats(
    client: TestClient, superuser_token_headers: dict[str, str], normal_user_token_headers: dict[str, str]
) -> None:
    assert client.get(f"{API}/stats/").status_code == 401
    assert client.get(f"{API}/stats/", headers=normal_user_token_headers).status_code == 403
    response = client.get(f"{API}/stats/", headers=superuser_token_headers)
    assert response.status_code == 200
    assert len(response.json()["weeks"]) == 12
