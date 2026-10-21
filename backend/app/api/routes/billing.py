"""Paid plans: start Stripe Checkout, open the customer portal, switch between plans, show a customer's
checks for the billing period and their history, and receive Stripe's webhook.
"""

import logging
import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

import stripe
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict
from sqlmodel import col, func, select

from app.api.billing import (
    active_plan,
    allowance,
    get_stripe,
    plans,
    stripe_client,
    stripe_id,
    sync_subscription,
)
from app.api.deps import CurrentUser, OptionalUserDep, SessionDep
from app.api.free_check import rate_limited, same_origin
from app.api.stripe_webhook import process_event
from app.core.config import settings
from app.models import Customer, PaidCheck, User, get_datetime_utc

logger = logging.getLogger(__name__)

router = APIRouter(tags=["billing"])

StripeDep = Annotated[stripe.StripeClient, Depends(get_stripe)]
PlanId = Literal["starter", "agency"]


class PlanIn(BaseModel):
    plan: PlanId


class RedirectOut(BaseModel):
    url: str


class BillingOut(BaseModel):
    checkout_enabled: bool  # Stripe is set up, so plans can be bought here
    has_billing: bool  # a Stripe customer exists, so the customer portal opens
    plan: PlanId | None  # the active plan
    plan_name: str | None
    status: str | None  # Stripe's subscription status, e.g. active, past_due, canceled
    checks_included: int
    checks_used: int  # this billing period, extra checks included
    extra_checks: int
    extra_checks_max: int
    period_start: datetime | None
    period_end: datetime | None
    cancel_at_period_end: bool


class PaidCheckPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    title: str | None
    status: str
    final_status: str | None
    extra: bool


class PaidChecksPublic(BaseModel):
    data: list[PaidCheckPublic]
    count: int


def _customer(session: SessionDep, user: User) -> Customer | None:
    return session.get(Customer, user.customer_id) if user.customer_id else None


def _billing(session: SessionDep, customer: Customer | None) -> BillingOut:
    plan = active_plan(customer)
    current = allowance(session, customer, plan, get_datetime_utc()) if customer and plan else None
    return BillingOut(
        checkout_enabled=settings.billing_enabled,
        has_billing=customer is not None,
        plan=plan.id if plan else None,  # type: ignore[arg-type]
        plan_name=plan.name if plan else None,
        status=customer.subscription_status if customer else None,
        checks_included=plan.checks if plan else 0,
        checks_used=current.used if current else 0,
        extra_checks=current.extra if current else 0,
        extra_checks_max=settings.PLAN_EXTRA_CHECKS_MAX,
        period_start=current.start if current else None,
        period_end=current.end if current else None,
        cancel_at_period_end=bool(customer and plan and customer.cancel_at_period_end),
    )


@router.get("/billing", response_model=BillingOut)
def read_billing(session: SessionDep, user: CurrentUser) -> Any:
    """The signed-in user's plan and the checks used this billing period."""
    return _billing(session, _customer(session, user))


@router.get("/billing/checks", response_model=PaidChecksPublic)
def read_paid_checks(session: SessionDep, user: CurrentUser, skip: int = 0, limit: int = 50) -> Any:
    """Checks that counted against the plan, newest first. Date, job title and result only, never the posting."""
    if user.customer_id is None:
        return PaidChecksPublic(data=[], count=0)
    mine = col(PaidCheck.customer_id) == user.customer_id
    count = session.exec(select(func.count()).select_from(PaidCheck).where(mine)).one()
    rows = session.exec(
        select(PaidCheck).where(mine).order_by(col(PaidCheck.created_at).desc()).offset(skip).limit(min(limit, 100))
    ).all()
    return PaidChecksPublic(data=[PaidCheckPublic.model_validate(row) for row in rows], count=count)


@router.post(
    "/billing/checkout", response_model=RedirectOut, dependencies=[Depends(rate_limited), Depends(same_origin)]
)
def start_checkout(body: PlanIn, session: SessionDep, user: OptionalUserDep, client: StripeDep) -> Any:
    """A Stripe Checkout page for the plan. Without a signed-in user, the account is created from the email
    given at Checkout (see the webhook)."""
    plan = plans()[body.plan]
    customer = _customer(session, user) if user else None
    if active_plan(customer):
        raise HTTPException(status_code=409, detail="You already have a plan. Change it from your account page.")
    params: dict[str, Any] = {
        "mode": "subscription",
        "line_items": [{"price": plan.price, "quantity": 1}, {"price": settings.STRIPE_PRICE_EXTRA_CHECK}],
        "success_url": f"{settings.FRONTEND_HOST}/welcome?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{settings.FRONTEND_HOST}/check#pricing",
        "consent_collection": {"terms_of_service": "required"},
        "custom_text": {
            "terms_of_service_acceptance": {
                "message": f"I agree to the [CheckON Terms of Service]({settings.FRONTEND_HOST}/terms)."
            }
        },
        "billing_address_collection": "required",
        "tax_id_collection": {"enabled": True},
        "automatic_tax": {"enabled": settings.STRIPE_AUTOMATIC_TAX},
        "subscription_data": {"metadata": {"plan": plan.id}},
        "metadata": {"plan": plan.id},
    }
    if user:
        params["client_reference_id"] = str(user.id)
    if customer:  # coming back after a plan ended: keep the same Stripe customer and invoices
        params["customer"] = customer.stripe_customer_id
        params["customer_update"] = {"address": "auto", "name": "auto"}
    elif user:
        params["customer_email"] = user.email
    try:
        checkout = client.v1.checkout.sessions.create(params)
    except stripe.StripeError as error:
        logger.error("Stripe Checkout failed: %s", error)
        raise HTTPException(status_code=503, detail="We couldn't open the payment page. Contact us to subscribe.")
    return RedirectOut(url=str(checkout.url))


@router.post("/billing/portal", response_model=RedirectOut)
def open_billing_portal(session: SessionDep, user: CurrentUser, client: StripeDep) -> Any:
    """Stripe's customer portal: card, invoices, cancelling."""
    customer = _customer(session, user)
    if customer is None:
        raise HTTPException(status_code=404, detail="There's no billing account for this user.")
    try:
        portal = client.v1.billing_portal.sessions.create(
            {"customer": customer.stripe_customer_id, "return_url": f"{settings.FRONTEND_HOST}/"}
        )
    except stripe.StripeError as error:
        logger.error("Stripe customer portal failed: %s", error)
        raise HTTPException(status_code=503, detail="We couldn't open billing. Try again in a minute.")
    return RedirectOut(url=str(portal.url))


@router.post("/billing/plan", response_model=BillingOut)
def change_plan(body: PlanIn, session: SessionDep, user: CurrentUser, client: StripeDep) -> Any:
    """Switch between Starter and Agency now. The price difference for the rest of the period is invoiced
    straight away, and the new plan's checks apply to the whole period. (Stripe's portal can't switch plans
    on a subscription with a usage-based price, so it happens here.)"""
    customer = _customer(session, user)
    current = active_plan(customer)
    if customer is None or current is None or customer.stripe_subscription_id is None:
        raise HTTPException(status_code=409, detail="There's no active plan to change.")
    if current.id == body.plan:
        raise HTTPException(status_code=409, detail=f"You're already on {current.name}.")
    target = plans()[body.plan]
    try:
        subscription = client.v1.subscriptions.retrieve(customer.stripe_subscription_id)
        item = next(item for item in subscription.items.data if stripe_id(item.price) == current.price)
        subscription = client.v1.subscriptions.update(
            subscription.id,
            {"items": [{"id": item.id, "price": target.price}], "proration_behavior": "always_invoice"},
        )
    except (stripe.StripeError, StopIteration) as error:
        logger.error("Plan change for customer %s failed: %s", customer.id, error)
        raise HTTPException(status_code=503, detail="We couldn't change your plan. Try again, or contact us.")
    sync_subscription(customer, subscription)
    session.add(customer)
    session.commit()
    return _billing(session, customer)


def _webhook_client() -> stripe.StripeClient:
    client = stripe_client()
    if client is None or not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Stripe isn't set up.")
    return client


@router.post("/stripe/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request, session: SessionDep, background: BackgroundTasks,
    client: Annotated[stripe.StripeClient, Depends(_webhook_client)],
) -> dict[str, bool]:  # fmt: skip
    """Stripe's events. The signature proves the request came from Stripe; anything else gets a 400."""
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, request.headers.get("stripe-signature"), settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook.")
    after = await run_in_threadpool(process_event, session, client, event)
    for action in after or []:
        background.add_task(action)
    return {"received": True, "duplicate": after is None}
