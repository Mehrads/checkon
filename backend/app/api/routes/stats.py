"""Usage numbers behind the PRD's success metrics (§2), for superusers only. v1 volumes are small, so the
numbers are worked out in Python from the raw rows.
"""

import math
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import SessionDep, get_current_active_superuser
from app.models import (
    ContactMessage,
    CustomRequest,
    Feedback,
    FreeCheckSpend,
    UsageEvent,
    get_datetime_utc,
)

TORONTO = ZoneInfo("America/Toronto")
WEEKS = 12
RETURN_WINDOW = timedelta(days=30)
RETURN_GAP = timedelta(days=1)  # a retry in the same visit isn't a return
TIMING_WINDOW = timedelta(days=30)

router = APIRouter(prefix="/stats", tags=["stats"], dependencies=[Depends(get_current_active_superuser)])


class Week(BaseModel):
    start: date  # Monday, Toronto time
    checks: int
    visitors: int  # distinct visitors who ran a check
    new_visitors: int  # ran their first check this week
    limit_hits: int  # tried again after using the week's free check
    refused: int  # pasted something that isn't one job posting
    fixes_applied: int  # checks whose fixes were applied
    custom_requests: int  # contact form "Custom setup", plus the older request form
    plan_enquiries: int  # contact form "Starter" or "Agency"
    contact_messages: int  # every contact form message
    feedback_up: int
    feedback_down: int  # down, or "looks wrong"
    model_spend_usd: Decimal


class Returning(BaseModel):
    """Visitors whose first check is at least 30 days old, and how many came back a day or more later but
    within 30 days (another check, or a try that hit the weekly limit). PRD target: 20%."""

    cohort: int
    returned: int
    rate: float | None


class Timing(BaseModel):
    """Seconds over the last 30 days. Findings: paste to results. Fixes: findings plus the suggested
    rewrite. PRD target: p95 under 15 seconds."""

    checks: int
    findings_p50: float | None
    findings_p95: float | None
    fixes_p50: float | None
    fixes_p95: float | None


class Totals(BaseModel):
    checks: int
    visitors: int
    fixes_applied: int
    custom_requests: int
    plan_enquiries: int
    contact_messages: int
    model_spend_usd: Decimal
    first_check: datetime | None


class StatsOut(BaseModel):
    generated_at: datetime
    totals: Totals
    weeks: list[Week]  # newest first
    returning: Returning
    timing: Timing


def _week(moment: datetime | date) -> date:
    if isinstance(moment, datetime):
        moment = (moment if moment.tzinfo else moment.replace(tzinfo=UTC)).astimezone(TORONTO).date()
    return moment - timedelta(days=moment.weekday())


def _percentile(values: list[float], share: float) -> float | None:
    """Nearest-rank percentile, in seconds to one decimal."""
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[max(math.ceil(share * len(ordered)) - 1, 0)], 1)


def compute_stats(session: Session, now: datetime) -> StatsOut:
    events = sorted(session.exec(select(UsageEvent)).all(), key=lambda e: e.at)
    requests = session.exec(select(CustomRequest.created_at)).all()
    contacts = session.exec(select(ContactMessage.created_at, ContactMessage.interest)).all()
    requests = [*requests, *(created for created, interest in contacts if interest == "custom")]
    plans = [created for created, interest in contacts if interest in ("starter", "agency")]
    feedback = session.exec(select(Feedback.created_at, Feedback.rating)).all()
    spend = session.exec(select(FreeCheckSpend)).all()

    checks = [e for e in events if e.kind == "check"]
    first_seen: dict[str, datetime] = {}
    for event in checks:
        if event.visitor:
            first_seen.setdefault(event.visitor, event.at)

    weeks = []
    for start in [_week(now) - timedelta(weeks=i) for i in range(WEEKS)]:

        def during(moment: datetime | date, start: date = start) -> bool:
            return _week(moment) == start

        week_checks = [e for e in checks if during(e.at)]
        weeks.append(Week(
            start=start,
            checks=len(week_checks),
            visitors=len({e.visitor for e in week_checks if e.visitor}),
            new_visitors=sum(1 for first in first_seen.values() if during(first)),
            limit_hits=sum(1 for e in events if e.kind == "quota" and during(e.at)),
            refused=sum(1 for e in events if e.kind == "refused" and during(e.at)),
            fixes_applied=len({e.check_id for e in events if e.kind == "accept" and during(e.at)}),
            custom_requests=sum(1 for at in requests if during(at)),
            plan_enquiries=sum(1 for at in plans if during(at)),
            contact_messages=sum(1 for at, _ in contacts if during(at)),
            feedback_up=sum(1 for at, rating in feedback if rating == "up" and during(at)),
            feedback_down=sum(1 for at, rating in feedback if rating != "up" and during(at)),
            model_spend_usd=sum((row.usd for row in spend if during(row.day)), Decimal(0)),
        ))  # fmt: skip

    visits: dict[str, list[datetime]] = defaultdict(list)
    for event in events:
        if event.visitor and event.kind in ("check", "quota"):
            visits[event.visitor].append(event.at)
    cohort = [visitor for visitor, first in first_seen.items() if first <= now - RETURN_WINDOW]
    returned = [
        visitor for visitor in cohort
        if any(first_seen[visitor] + RETURN_GAP <= at <= first_seen[visitor] + RETURN_WINDOW for at in visits[visitor])
    ]  # fmt: skip

    refine_ms: dict[str, int] = {}
    for event in events:
        if event.kind == "refine" and event.status == "ok" and event.check_id and event.duration_ms is not None:
            refine_ms.setdefault(event.check_id, event.duration_ms)  # the first rewrite is the one people wait for
    recent = [e for e in checks if e.at >= now - TIMING_WINDOW and e.duration_ms is not None]
    findings = [e.duration_ms / 1000 for e in recent if e.duration_ms is not None]
    fixes = [
        (e.duration_ms + refine_ms[e.check_id]) / 1000
        for e in recent if e.duration_ms is not None and e.check_id in refine_ms
    ]  # fmt: skip

    return StatsOut(
        generated_at=now,
        totals=Totals(
            checks=len(checks),
            visitors=len(first_seen),
            fixes_applied=len({e.check_id for e in events if e.kind == "accept"}),
            custom_requests=len(requests),
            plan_enquiries=len(plans),
            contact_messages=len(contacts),
            model_spend_usd=sum((row.usd for row in spend), Decimal(0)),
            first_check=checks[0].at if checks else None,
        ),
        weeks=weeks,
        returning=Returning(
            cohort=len(cohort), returned=len(returned), rate=round(len(returned) / len(cohort), 3) if cohort else None
        ),
        timing=Timing(
            checks=len(recent),
            findings_p50=_percentile(findings, 0.5),
            findings_p95=_percentile(findings, 0.95),
            fixes_p50=_percentile(fixes, 0.5),
            fixes_p95=_percentile(fixes, 0.95),
        ),
    )


@router.get("/", response_model=StatsOut)
def read_stats(session: SessionDep) -> Any:
    return compute_stats(session, get_datetime_utc())
