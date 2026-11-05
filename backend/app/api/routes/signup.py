"""Sign-up: an account for an email address, with no card. Signing up emails a link to set the password, which
also proves the address; the account then logs in like any other, with its password and an emailed code.

Off unless SIGNUP_OPEN is set: every account's checks are paid for by whoever runs the server, so by default only
an admin adds users (Admin > Users). Signed-in accounts are limited by ACCOUNT_CHECKS_PER_30_DAYS, if set.
"""

import logging
import secrets
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from pydantic import BaseModel, EmailStr
from sqlmodel import func, select

from app.api.deps import SessionDep
from app.api.free_check import RateLimiter, client_ip, refused, same_origin
from app.core.config import settings
from app.core.security import get_password_hash
from app.models import Message, User
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
CLOSED = "Sign-up is closed on this server. Ask its admin for an account."


class SignupIn(BaseModel):
    email: EmailStr


def generate_signup_email(email_to: str, link: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    html_content = render_email_template(
        template_name="new_signup.html",
        context={
            "project_name": project_name,
            "username": email_to,
            "valid_hours": settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS,
            "link": link,
            "login_link": f"{settings.FRONTEND_HOST}/login",
        },
    )
    return EmailData(html_content=html_content, subject=f"Set your {project_name} password")


def _send(email: EmailData, to: str, link: str) -> None:
    if not settings.emails_enabled:
        logger.info(f"Sign-up link for {to}: {link}")
        logger.warning("SMTP isn't set up, so %s wasn't emailed a sign-up link", to)
        return
    try:
        send_email(email_to=to, subject=email.subject, html_content=email.html_content)
    except Exception:  # the account exists; "Forgot your password?" sends a new link
        logger.exception("Could not email the sign-up link to %s", to)


def send_signup_email(email: str) -> None:
    query = {"token": generate_password_reset_token(email=email), "new": "1"}
    link = f"{settings.FRONTEND_HOST}/reset-password?{urlencode(query)}"
    _send(generate_signup_email(email, link), email, link)


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
    """An account for the email, and the link to set its password. The answer is the same whether or not the
    address has an account, so the form can't tell anyone who signed up."""
    if not settings.SIGNUP_OPEN:
        raise refused(403, "signup_closed", CLOSED)
    if not _signups.allow(client_ip(request)):
        raise refused(
            429, "rate_limit", "Too many sign-ups from here. Try again in an hour."
        )
    email = str(body.email).strip().lower()
    user = session.exec(select(User).where(func.lower(User.email) == email)).first()
    if user is not None:
        background.add_task(send_existing_account_email, user.email)
        return Message(message=SENT)
    session.add(
        User(email=email, hashed_password=get_password_hash(secrets.token_urlsafe(32)))
    )
    session.commit()
    background.add_task(send_signup_email, email)
    return Message(message=SENT)
