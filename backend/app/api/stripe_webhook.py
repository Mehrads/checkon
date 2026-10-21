"""Stripe webhook events. Each event is applied once, in one transaction. Events can arrive out of order, so
the subscription is always read fresh from Stripe rather than taken from the event.

A completed Checkout creates the customer's account (public sign-up is off) and emails a link to set a
password. Emails go out only after the transaction commits, so a retried event can't send a second one.
"""

import logging
import secrets
import uuid
from collections.abc import Callable
from typing import Any

import stripe
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, func, select

from app.api.billing import (
    active_plan,
    customer_for,
    plans,
    stripe_id,
    sync_subscription,
)
from app.core.config import settings
from app.core.security import get_password_hash
from app.models import Customer, StripeEvent, User
from app.utils import (
    generate_password_reset_token,
    generate_set_password_email,
    send_email,
)

logger = logging.getLogger(__name__)

# The events the webhook endpoint subscribes to (infra/README.md, "Stripe")
EVENTS = {
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.paid",
    "invoice.payment_failed",
}

After = list[Callable[[], None]]
_email = TypeAdapter(EmailStr)


def process_event(session: Session, client: stripe.StripeClient, event: stripe.Event) -> bool:
    """Apply one event. False if it was already applied (Stripe redelivers events)."""
    session.add(StripeEvent(id=event.id, type=event.type))
    try:
        session.flush()  # a second delivery waits here for the first to commit, then fails
    except IntegrityError:
        session.rollback()
        return False
    after: After = []
    data = event.data.object
    if event.type == "checkout.session.completed":
        _checkout_completed(session, client, data, after)
    elif event.type.startswith("customer.subscription."):
        _sync(session, client, data.id)
    elif event.type in ("invoice.paid", "invoice.payment_failed"):
        if subscription := _invoice_subscription(data):
            _sync(session, client, subscription)
    session.commit()
    for action in after:
        action()
    return True


def _sync(session: Session, client: stripe.StripeClient, subscription_id: str) -> Customer:
    subscription = client.v1.subscriptions.retrieve(subscription_id)
    customer = customer_for(session, stripe_id(subscription.customer))
    sync_subscription(customer, subscription)
    session.add(customer)
    return customer


def _invoice_subscription(invoice: Any) -> str | None:
    parent = getattr(invoice, "parent", None)
    details = getattr(parent, "subscription_details", None) if parent else None
    subscription = getattr(details, "subscription", None) if details else None
    # Webhook endpoints on API versions before 2025-03-31 send it on the invoice itself
    subscription = subscription or getattr(invoice, "subscription", None)
    return stripe_id(subscription) if subscription else None


def _checkout_completed(session: Session, client: stripe.StripeClient, checkout: Any, after: After) -> None:
    if checkout.mode != "subscription" or not checkout.customer:
        return
    details = getattr(checkout, "customer_details", None)
    email = getattr(details, "email", None) if details else None
    email = (email or getattr(checkout, "customer_email", None) or "").strip().lower() or None
    customer = customer_for(session, stripe_id(checkout.customer), email)
    if checkout.subscription:
        customer = _sync(session, client, stripe_id(checkout.subscription))
    _attach_user(session, customer, email, getattr(checkout, "client_reference_id", None), after)


def _attach_user(session: Session, customer: Customer, email: str | None, reference: str | None, after: After) -> None:
    """Link the account that paid: the signed-in user who started Checkout, else the user with the Checkout
    email, else a new account."""
    user = None
    if reference:
        try:
            user = session.get(User, uuid.UUID(reference))
        except ValueError:
            pass
    if user is None and email:
        user = session.exec(select(User).where(func.lower(User.email) == email)).first()
    if user is None:
        try:
            email = _email.validate_python(email)
        except ValidationError:  # the API's user model would refuse it
            logger.error("Checkout for Stripe customer %s has no usable email; no account created", customer.stripe_customer_id)
            return
        user = User(email=email, hashed_password=get_password_hash(secrets.token_urlsafe(32)))
        plan = plans().get(customer.plan or "")
        after.append(lambda: send_set_password_email(email, plan.name if plan else None))
    if user.customer_id is not None and user.customer_id != customer.id:
        earlier = session.get(Customer, user.customer_id)
        if active_plan(earlier):
            logger.error(
                "User %s already has a plan with Stripe customer %s; Stripe customer %s also subscribed. Refund one.",
                user.id, earlier.stripe_customer_id if earlier else "?", customer.stripe_customer_id,
            )  # fmt: skip
            return
    user.customer_id = customer.id
    session.add(user)


def send_set_password_email(email: str, plan_name: str | None) -> None:
    link = f"{settings.FRONTEND_HOST}/reset-password?token={generate_password_reset_token(email=email)}"
    email_data = generate_set_password_email(email_to=email, plan_name=plan_name, link=link)
    if settings.FASTAPI_ENV == "development":
        logger.info(f"Set-password link for {email}: {link}")
    if not settings.emails_enabled:
        logger.warning("SMTP isn't set up, so %s wasn't emailed a set-password link", email)
        return
    try:
        send_email(email_to=email, subject=email_data.subject, html_content=email_data.html_content)
    except Exception:  # the account exists; "Forgot your password?" sends a new link
        logger.exception("Could not email the set-password link to %s", email)
