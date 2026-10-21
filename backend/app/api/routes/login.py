import hmac
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import col, delete, select

from app import crud
from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.core import security
from app.core.config import settings
from app.models import (
    LoginChallenge,
    LoginCode,
    LoginCodeIn,
    Message,
    NewPassword,
    Token,
    User,
    UserPublic,
    UserUpdate,
)
from app.utils import (
    generate_login_code_email,
    generate_password_reset_token,
    generate_reset_password_email,
    send_email,
    verify_password_reset_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["login"])


@router.post("/login/password")
def login_password(
    session: SessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> LoginChallenge:
    """
    Check the email and password, then email a sign-in code for /login/access-token
    """
    user = crud.authenticate(
        session=session, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    now = datetime.now(UTC)
    session.exec(
        delete(LoginCode).where(
            col(LoginCode.user_id) == user.id,
            col(LoginCode.created_at) < now - timedelta(hours=1),
        )
    )
    recent = session.exec(
        select(LoginCode).where(col(LoginCode.user_id) == user.id)
    ).all()
    if len(recent) >= settings.LOGIN_CODES_PER_HOUR:
        raise HTTPException(
            status_code=429, detail="Too many sign-in codes. Try again in an hour."
        )

    challenge = secrets.token_urlsafe(32)
    code = security.new_login_code()
    session.add(
        LoginCode(
            user_id=user.id,
            challenge_hash=security.hash_login_challenge(challenge),
            code_hash=security.hash_login_code(challenge, code),
            expires_at=now + timedelta(minutes=settings.LOGIN_CODE_EXPIRE_MINUTES),
        )
    )
    session.commit()

    development = settings.FASTAPI_ENV == "development"
    if development:
        logger.info(f"Sign-in code for {user.email}: {code}")
    email_data = generate_login_code_email(email_to=user.email, code=code)
    sent = settings.emails_enabled and send_email(
        email_to=user.email,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    if not sent and not development:
        raise HTTPException(
            status_code=503,
            detail="We couldn't email your sign-in code. Try again later.",
        )
    return LoginChallenge(challenge=challenge)


@router.post("/login/access-token")
def login_access_token(session: SessionDep, body: LoginCodeIn) -> Token:
    """
    Exchange the emailed sign-in code for an access token
    """
    # Lock the row so parallel guesses can't get past the attempt limit
    login_code = session.exec(
        select(LoginCode)
        .where(
            col(LoginCode.challenge_hash)
            == security.hash_login_challenge(body.challenge)
        )
        .with_for_update()
    ).first()
    if (
        not login_code
        or login_code.expires_at < datetime.now(UTC)
        or login_code.attempts >= settings.LOGIN_CODE_MAX_ATTEMPTS
    ):
        raise HTTPException(
            status_code=400, detail="This code has expired. Log in again."
        )
    expected = security.hash_login_code(body.challenge, body.code)
    if not hmac.compare_digest(login_code.code_hash, expected):
        login_code.attempts += 1
        used_up = login_code.attempts >= settings.LOGIN_CODE_MAX_ATTEMPTS
        session.add(login_code)
        session.commit()
        if used_up:
            raise HTTPException(
                status_code=400, detail="Too many wrong codes. Log in again."
            )
        raise HTTPException(status_code=400, detail="Incorrect code")

    user = session.get(User, login_code.user_id)
    session.delete(login_code)
    session.commit()
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
    )


@router.post("/login/test-token", response_model=UserPublic)
def test_token(current_user: CurrentUser) -> Any:
    """
    Test access token
    """
    return current_user


@router.post("/password-recovery/{email}")
def recover_password(email: str, session: SessionDep) -> Message:
    """
    Password Recovery
    """
    user = crud.get_user_by_email(session=session, email=email)

    # Always return the same response to prevent email enumeration attacks
    # Only send email if user actually exists
    if user:
        password_reset_token = generate_password_reset_token(email=email)
        email_data = generate_reset_password_email(
            email_to=user.email, email=email, token=password_reset_token
        )
        send_email(
            email_to=user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return Message(
        message="If that email is registered, we sent a password recovery link"
    )


@router.post("/reset-password/")
def reset_password(session: SessionDep, body: NewPassword) -> Message:
    """
    Reset password
    """
    email = verify_password_reset_token(token=body.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = crud.get_user_by_email(session=session, email=email)
    if not user:
        # Don't reveal that the user doesn't exist - use same error as invalid token
        raise HTTPException(status_code=400, detail="Invalid token")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    user_in_update = UserUpdate(password=body.new_password)
    crud.update_user(
        session=session,
        db_user=user,
        user_in=user_in_update,
    )
    return Message(message="Password updated successfully")


@router.post(
    "/password-recovery-html-content/{email}",
    dependencies=[Depends(get_current_active_superuser)],
    response_class=HTMLResponse,
)
def recover_password_html_content(email: str, session: SessionDep) -> Any:
    """
    HTML Content for Password Recovery
    """
    user = crud.get_user_by_email(session=session, email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )
    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )

    return HTMLResponse(
        content=email_data.html_content, headers={"subject:": email_data.subject}
    )
