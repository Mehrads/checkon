"""Free accounts: sign up with an email, no card. The account gets the free plan (PLAN_CHECKS_FREE checks every 30
days from sign-up) and keeps the history of its checks; company profiles, pay suggestions, audits and the archive
stay with the paid plans. Signing up emails a link to set the password, which also proves the address; the account
then logs in like any other, with its password and an emailed code. A visitor who signed up from an outreach report
comes back to it after logging in, and it's saved to the account.
"""

import logging
import secrets
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import func, select

from app.api.billing import free_customer
from app.api.deps import SessionDep
from app.api.free_check import RateLimiter, client_ip, refused, same_origin
from app.core.config import settings
from app.core.security import get_password_hash
from app.models import Message, OutreachReport, User, get_datetime_utc
from app.utils import (
    EmailData,
    generate_password_reset_token,
    generate_reset_password_email,
    render_email_template,
    send_email,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["signup"])

_signups = RateLimiter(settings.SIGNUPS_PER_HOUR, window_seconds=3600)
SENT = "Check your email for a link to set your password."


class SignupIn(BaseModel):
    email: EmailStr
    report: str | None = Field(
        default=None, max_length=64
    )  # an outreach report's token, to save once signed in


def generate_free_account_email(
    email_to: str, link: str, company: str | None
) -> EmailData:
    project_name = settings.PROJECT_NAME
    saved = f"{company}'s report is waiting there for you." if company else ""
    html_content = render_email_template(
        template_name="free_account.html",
        context={
            "project_name": project_name,
            "username": email_to,
            "checks": settings.PLAN_CHECKS_FREE,
            "saved": saved,
            "valid_hours": settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
            "link": link,
            "login_link": f"{settings.FRONTEND_HOST}/login",
        },
    )
    return EmailData(
        html_content=html_content, subject=f"Set your {project_name} password"
    )


def _send(email: EmailData, to: str, link: str) -> None:
    if not settings.emails_enabled:
        logger.info(f"Sign-up link for {to}: {link}")
        logger.warning("SMTP isn't set up, so %s wasn't emailed a sign-up link", to)
        return
    try:
        send_email(email_to=to, subject=email.subject, html_content=email.html_content)
    except Exception:  # the account exists; "Forgot your password?" sends a new link
        logger.exception("Could not email the sign-up link to %s", to)


def send_free_account_email(email: str, report: tuple[str, str] | None) -> None:
    """report: the outreach report's token and company, when they signed up from it."""
    query = {"token": generate_password_reset_token(email=email), "new": "1"}
    if report is not None:  # back to the report after logging in, which saves it
        query["next"] = f"/report/{report[0]}?save=1"
    link = f"{settings.FRONTEND_HOST}/reset-password?{urlencode(query)}"
    _send(
        generate_free_account_email(email, link, report[1] if report else None),
        email,
        link,
    )


def send_existing_account_email(email: str) -> None:
    """Someone signed up with an address that has an account: a link to set a new password, so they get in."""
    token = generate_password_reset_token(email=email)
    _send(generate_reset_password_email(email_to=email, email=email, token=token), email,
          f"{settings.FRONTEND_HOST}/reset-password?token={token}")  # fmt: skip


@router.post(
    "/signup",
    status_code=202,
    response_model=Message,
    dependencies=[Depends(same_origin)],
)
def sign_up(
    body: SignupIn, request: Request, session: SessionDep, background: BackgroundTasks
) -> Any:
    """A free account for the email, and the link to set its password. The answer is the same whether or not the
    address has an account, so the form can't tell anyone who signed up."""
    if not _signups.allow(client_ip(request)):
        raise refused(
            429, "rate_limit", "Too many sign-ups from here. Try again in an hour."
        )
    email = str(body.email).strip().lower()
    report = None
    if body.report:
        found = session.exec(
            select(OutreachReport).where(OutreachReport.token == body.report)
        ).first()
        report = (
            (found.token, found.company)
            if found is not None and found.customer_id is None
            else None
        )
    user = session.exec(select(User).where(func.lower(User.email) == email)).first()
    if user is not None:
        background.add_task(send_existing_account_email, user.email)
        return Message(message=SENT)
    customer = free_customer(email, get_datetime_utc())
    session.add(customer)
    session.flush()
    session.add(
        User(
            email=email,
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),
            customer_id=customer.id,
        )
    )
    session.commit()
    background.add_task(send_free_account_email, email, report)
    return Message(message=SENT)
