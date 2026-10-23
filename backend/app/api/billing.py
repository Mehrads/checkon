"""Paid plans on Stripe Billing: the plans, the Stripe client, the checks a customer has left in the billing
period, and our copy of each subscription. Card details never reach us: Checkout and the customer portal
are pages hosted by Stripe.

A plan's monthly fee is a flat price billed in advance. Checks past the plan's allowance are sent to a Stripe
meter, one event per extra check, and billed in arrears on the next invoice at the extra-check price.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cache
from typing import Any

import stripe
from fastapi import HTTPException
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, col, func, select

from app.core.config import settings
from app.core.db import engine
from app.models import Customer, PaidCheck, User, get_datetime_utc

logger = logging.getLogger(__name__)

# Stripe keeps retrying the card while a subscription is past due, so checks keep working meanwhile.
ACTIVE = {"active", "trialing", "past_due"}
# Stripe accepts meter events up to 35 days old.
METER_WINDOW = timedelta(days=34)


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    checks: int  # included in each billing period
    price: str | None  # the Stripe price of the monthly fee


def plans() -> dict[str, Plan]:
    return {
        "starter": Plan("starter", "Starter", settings.PLAN_CHECKS_STARTER, settings.STRIPE_PRICE_STARTER),
        "agency": Plan("agency", "Agency", settings.PLAN_CHECKS_AGENCY, settings.STRIPE_PRICE_AGENCY),
    }


def plan_for_price(price_id: str) -> Plan | None:
    return next((plan for plan in plans().values() if plan.price == price_id), None)


# The Stripe client


@cache
def _client(api_key: str) -> stripe.StripeClient:
    return stripe.StripeClient(api_key, max_network_retries=2)


def stripe_client() -> stripe.StripeClient | None:
    """None until Stripe is set up (the key and the three prices)."""
    if not settings.billing_enabled or not settings.STRIPE_SECRET_KEY:
        return None
    return _client(settings.STRIPE_SECRET_KEY)


def get_stripe() -> stripe.StripeClient:
    client = stripe_client()
    if client is None:
        raise HTTPException(status_code=503, detail="Paid plans aren't open yet. Contact us to subscribe.")
    return client


def stripe_id(value: Any) -> str:
    """The id of a field Stripe may send as an id or as the expanded object."""
    return value if isinstance(value, str) else str(value.id)


# The plan's checks


@dataclass(frozen=True)
class Allowance:
    plan: Plan
    start: datetime
    end: datetime
    used: int  # checks this period, extra ones included

    @property
    def extra(self) -> int:
        return max(self.used - self.plan.checks, 0)

    @property
    def exhausted(self) -> bool:
        return self.extra >= settings.PLAN_EXTRA_CHECKS_MAX


def active_plan(customer: Customer | None) -> Plan | None:
    if customer is None or customer.plan is None or customer.subscription_status not in ACTIVE:
        return None
    return plans().get(customer.plan)


def billing_period(customer: Customer, now: datetime) -> tuple[datetime, datetime]:
    start, end = customer.current_period_start, customer.current_period_end
    if start is None or end is None or end <= start:  # not synced yet: the last 30 days
        return now - timedelta(days=30), now + timedelta(seconds=1)
    while end <= now:  # the renewal hasn't reached us yet, so the next period has started
        start, end = end, end + (end - start)
    return start, end


def allowance(session: Session, customer: Customer, plan: Plan, now: datetime) -> Allowance:
    start, end = billing_period(customer, now)
    used = session.exec(
        select(func.count()).select_from(PaidCheck).where(
            PaidCheck.customer_id == customer.id, PaidCheck.created_at >= start, PaidCheck.created_at < end
        )
    ).one()  # fmt: skip
    return Allowance(plan, start, end, used)


@dataclass(frozen=True)
class PlanAccess:
    """A signed-in user whose customer has an active plan."""

    user: User
    customer: Customer
    plan: Plan


def plan_access(session: Session, user: User | None) -> PlanAccess | None:
    if user is None or user.customer_id is None:
        return None
    customer = session.get(Customer, user.customer_id)
    plan = active_plan(customer)
    return PlanAccess(user, customer, plan) if customer and plan else None


class PlanLimits:
    """The plan's checks for one signed-in customer, in Postgres."""

    def __init__(self, session: Session, access: PlanAccess) -> None:
        self.session = session
        self.access = access

    @property
    def plan(self) -> Plan:
        return self.access.plan

    @property
    def customer_id(self) -> uuid.UUID:
        return self.access.customer.id

    def next_check(self) -> datetime | None:
        """When checks start again, if this period's checks and extra checks are used up."""
        now = get_datetime_utc()
        current = allowance(self.session, self.access.customer, self.plan, now)
        return current.end if current.exhausted else None

    def record(self, check_id: str, title: str | None, status: str, workspace_id: uuid.UUID | None = None) -> PaidCheck:
        """Count a check against the plan, whichever workspace it's for. The customer row is locked so two
        checks at once can't both take the last included check."""
        now = get_datetime_utc()
        customer = self.session.exec(select(Customer).where(Customer.id == self.customer_id).with_for_update()).one()
        used = allowance(self.session, customer, self.plan, now).used
        check = PaidCheck(
            created_at=now, customer_id=customer.id, user_id=self.access.user.id, check_id=check_id,
            title=title[:255] if title else None, status=status, extra=used >= self.plan.checks,
            workspace_id=workspace_id,
        )  # fmt: skip
        self.session.add(check)
        self.session.commit()
        self.session.refresh(check)
        return check


def record_final_status(session: Session, check_id: str, status: str) -> None:
    check = session.exec(select(PaidCheck).where(PaidCheck.check_id == check_id)).first()
    if check is not None:
        check.final_status = status
        session.add(check)
        session.commit()


def report_extra_checks(client: stripe.StripeClient, session: Session, customer_id: uuid.UUID) -> int:
    """Send the customer's unreported extra checks to the meter; returns how many went. A check that fails
    is retried after the customer's next check. Stripe ignores a repeated identifier, so a retry can't bill
    twice. A complimentary account has nothing to bill."""
    customer = session.get(Customer, customer_id)
    if customer is None or customer.complimentary or customer.stripe_customer_id is None:
        return 0
    pending = session.exec(
        select(PaidCheck)
        .where(
            PaidCheck.customer_id == customer_id, col(PaidCheck.extra), col(PaidCheck.reported_at).is_(None),
            PaidCheck.created_at > get_datetime_utc() - METER_WINDOW,
        )
        .order_by(col(PaidCheck.created_at))
    ).all()  # fmt: skip
    sent = 0
    for check in pending:
        try:
            client.v1.billing.meter_events.create({
                "event_name": settings.STRIPE_METER_EVENT,
                "payload": {"stripe_customer_id": customer.stripe_customer_id, "value": "1"},
                "identifier": str(check.id),
                "timestamp": int(check.created_at.timestamp()),
            })  # fmt: skip
        except stripe.StripeError:
            logger.exception("Could not send extra check %s to Stripe", check.id)
            break
        check.reported_at = get_datetime_utc()
        session.add(check)
        session.commit()
        sent += 1
    return sent


def report_extra_checks_later(client: stripe.StripeClient, customer_id: uuid.UUID) -> None:
    """For a background task, which runs after the request's own session has closed."""
    with Session(engine) as session:
        report_extra_checks(client, session, customer_id)


# Our copy of the subscription


def customer_for(session: Session, stripe_customer_id: str, email: str | None = None) -> Customer:
    """The customer for a Stripe customer id, created on first sight (two webhooks may race to do it)."""
    session.exec(
        insert(Customer)
        .values(id=uuid.uuid4(), created_at=get_datetime_utc(), stripe_customer_id=stripe_customer_id,
                email=email, cancel_at_period_end=False)
        .on_conflict_do_nothing(index_elements=["stripe_customer_id"])
    )  # fmt: skip
    customer = session.exec(select(Customer).where(Customer.stripe_customer_id == stripe_customer_id)).one()
    if email and not customer.email:
        customer.email = email
    return customer


def _when(timestamp: int | None) -> datetime | None:
    return datetime.fromtimestamp(timestamp, UTC) if timestamp else None


def sync_subscription(customer: Customer, subscription: stripe.Subscription) -> None:
    """Copy the subscription's plan, status and billing period onto the customer."""
    current = customer.stripe_subscription_id
    if current not in (None, subscription.id) and active_plan(customer) and subscription.status not in ACTIVE:
        return  # an older subscription ending leaves the current one alone
    item = next((item for item in subscription.items.data if plan_for_price(stripe_id(item.price))), None)
    plan = plan_for_price(stripe_id(item.price)) if item else None
    if plan is None:
        logger.warning("Subscription %s has none of the plan prices", subscription.id)
    customer.stripe_subscription_id = subscription.id
    customer.plan = plan.id if plan else None
    customer.subscription_status = subscription.status
    customer.current_period_start = _when(item.current_period_start) if item else None
    customer.current_period_end = _when(item.current_period_end) if item else None
    customer.cancel_at_period_end = bool(subscription.cancel_at_period_end or getattr(subscription, "cancel_at", None))
