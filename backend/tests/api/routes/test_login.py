from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlmodel import Session, col, select

from app.core.config import settings
from app.core.security import get_password_hash, hash_login_challenge, verify_password
from app.crud import create_user
from app.models import LoginCode, User, UserCreate
from app.utils import generate_password_reset_token
from tests.utils.user import create_random_user, user_authentication_headers
from tests.utils.utils import LOGIN_CODE, random_email, random_lower_string


@pytest.fixture
def sent_emails() -> Generator[list[dict[str, Any]]]:
    """Capture the sign-in emails, whose code is always LOGIN_CODE."""
    sent: list[dict[str, Any]] = []
    with (
        patch("app.core.security.new_login_code", return_value=LOGIN_CODE),
        patch(
            "app.api.routes.login.send_email",
            side_effect=lambda **kwargs: sent.append(kwargs) or True,
        ),
    ):
        yield sent


def request_code(client: TestClient, email: str, password: str) -> str:
    r = client.post(
        f"{settings.API_V1_STR}/login/password",
        data={"username": email, "password": password},
    )
    assert r.status_code == 200, r.json()
    return str(r.json()["challenge"])


def send_code(client: TestClient, challenge: str, code: str) -> Any:
    return client.post(
        f"{settings.API_V1_STR}/login/access-token",
        json={"challenge": challenge, "code": code},
    )


def new_user(db: Session) -> tuple[str, str]:
    email, password = random_email(), random_lower_string()
    create_user(session=db, user_create=UserCreate(email=email, password=password))
    return email, password


def test_get_access_token(
    client: TestClient, sent_emails: list[dict[str, Any]]
) -> None:
    challenge = request_code(
        client, settings.FIRST_SUPERUSER, settings.FIRST_SUPERUSER_PASSWORD
    )
    assert len(sent_emails) == 1
    assert sent_emails[0]["email_to"] == settings.FIRST_SUPERUSER
    assert f">{LOGIN_CODE}<" in sent_emails[0]["html_content"]

    r = send_code(client, challenge, LOGIN_CODE)
    tokens = r.json()
    assert r.status_code == 200
    assert tokens["access_token"]


def test_get_access_token_incorrect_password(
    client: TestClient, sent_emails: list[dict[str, Any]]
) -> None:
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": "incorrect",
    }
    r = client.post(f"{settings.API_V1_STR}/login/password", data=login_data)
    assert r.status_code == 400
    assert sent_emails == []


@pytest.mark.usefixtures("sent_emails")
def test_password_alone_gives_no_token(client: TestClient, db: Session) -> None:
    email, password = new_user(db)
    r = client.post(
        f"{settings.API_V1_STR}/login/password",
        data={"username": email, "password": password},
    )
    assert r.status_code == 200
    assert set(r.json()) == {"challenge"}


@pytest.mark.usefixtures("sent_emails")
def test_wrong_code(client: TestClient, db: Session) -> None:
    email, password = new_user(db)
    challenge = request_code(client, email, password)

    r = send_code(client, challenge, "000000")
    assert r.status_code == 400
    assert r.json()["detail"] == "Incorrect code"
    # A wrong code doesn't use up the challenge
    assert send_code(client, challenge, LOGIN_CODE).status_code == 200


@pytest.mark.usefixtures("sent_emails")
def test_too_many_wrong_codes(client: TestClient, db: Session) -> None:
    email, password = new_user(db)
    challenge = request_code(client, email, password)

    for _ in range(settings.LOGIN_CODE_MAX_ATTEMPTS - 1):
        assert send_code(client, challenge, "000000").json()["detail"] == (
            "Incorrect code"
        )
    r = send_code(client, challenge, "000000")
    assert r.json()["detail"] == "Too many wrong codes. Log in again."

    r = send_code(client, challenge, LOGIN_CODE)
    assert r.status_code == 400
    assert r.json()["detail"] == "This code has expired. Log in again."


@pytest.mark.usefixtures("sent_emails")
def test_expired_code(client: TestClient, db: Session) -> None:
    email, password = new_user(db)
    challenge = request_code(client, email, password)
    login_code = db.exec(
        select(LoginCode).where(
            col(LoginCode.challenge_hash) == hash_login_challenge(challenge)
        )
    ).one()
    login_code.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.add(login_code)
    db.commit()

    r = send_code(client, challenge, LOGIN_CODE)
    assert r.status_code == 400
    assert r.json()["detail"] == "This code has expired. Log in again."


@pytest.mark.usefixtures("sent_emails")
def test_code_works_once(client: TestClient, db: Session) -> None:
    email, password = new_user(db)
    challenge = request_code(client, email, password)

    assert send_code(client, challenge, LOGIN_CODE).status_code == 200
    assert send_code(client, challenge, LOGIN_CODE).status_code == 400


def test_unknown_challenge(client: TestClient) -> None:
    r = send_code(client, "not-a-challenge", LOGIN_CODE)
    assert r.status_code == 400


def test_code_must_be_six_digits(client: TestClient) -> None:
    r = send_code(client, "not-a-challenge", "12345a")
    assert r.status_code == 422


def test_login_codes_per_hour(
    client: TestClient, db: Session, sent_emails: list[dict[str, Any]]
) -> None:
    email, password = new_user(db)
    for _ in range(settings.LOGIN_CODES_PER_HOUR):
        request_code(client, email, password)

    r = client.post(
        f"{settings.API_V1_STR}/login/password",
        data={"username": email, "password": password},
    )
    assert r.status_code == 429
    assert len(sent_emails) == settings.LOGIN_CODES_PER_HOUR


def test_login_code_email_failure(client: TestClient, db: Session) -> None:
    email, password = new_user(db)
    with (
        patch("app.core.config.settings.FASTAPI_ENV", None),
        patch("app.api.routes.login.send_email", return_value=False),
    ):
        r = client.post(
            f"{settings.API_V1_STR}/login/password",
            data={"username": email, "password": password},
        )
    assert r.status_code == 503


@pytest.mark.usefixtures("sent_emails")
def test_deleting_user_deletes_login_codes(client: TestClient, db: Session) -> None:
    user = create_random_user(db)
    password = random_lower_string()
    user.hashed_password = get_password_hash(password)
    db.add(user)
    db.commit()
    request_code(client, user.email, password)
    user_id = user.id

    db.delete(user)
    db.commit()
    codes = db.exec(select(LoginCode).where(col(LoginCode.user_id) == user_id))
    assert codes.all() == []


def test_use_access_token(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    r = client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers=superuser_token_headers,
    )
    result = r.json()
    assert r.status_code == 200
    assert "email" in result


def test_recovery_password(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    with (
        patch("app.core.config.settings.SMTP_HOST", "smtp.example.com"),
        patch("app.core.config.settings.SMTP_USER", "admin@example.com"),
    ):
        email = "test@example.com"
        r = client.post(
            f"{settings.API_V1_STR}/password-recovery/{email}",
            headers=normal_user_token_headers,
        )
        assert r.status_code == 200
        assert r.json() == {
            "message": "If that email is registered, we sent a password recovery link"
        }


def test_recovery_password_user_not_exits(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    email = "jVgQr@example.com"
    r = client.post(
        f"{settings.API_V1_STR}/password-recovery/{email}",
        headers=normal_user_token_headers,
    )
    # Should return 200 with generic message to prevent email enumeration attacks
    assert r.status_code == 200
    assert r.json() == {
        "message": "If that email is registered, we sent a password recovery link"
    }


def test_reset_password(client: TestClient, db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    new_password = random_lower_string()

    user_create = UserCreate(
        email=email,
        full_name="Test User",
        password=password,
        is_active=True,
        is_superuser=False,
    )
    user = create_user(session=db, user_create=user_create)
    token = generate_password_reset_token(email=email)
    headers = user_authentication_headers(client=client, email=email, password=password)
    data = {"new_password": new_password, "token": token}

    r = client.post(
        f"{settings.API_V1_STR}/reset-password/",
        headers=headers,
        json=data,
    )

    assert r.status_code == 200
    assert r.json() == {"message": "Password updated successfully"}

    db.refresh(user)
    verified, _ = verify_password(new_password, user.hashed_password)
    assert verified


def test_reset_password_invalid_token(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    data = {"new_password": "changethis", "token": "invalid"}
    r = client.post(
        f"{settings.API_V1_STR}/reset-password/",
        headers=superuser_token_headers,
        json=data,
    )
    response = r.json()

    assert "detail" in response
    assert r.status_code == 400
    assert response["detail"] == "Invalid token"


@pytest.mark.usefixtures("sent_emails")
def test_login_with_bcrypt_password_upgrades_to_argon2(
    client: TestClient, db: Session
) -> None:
    """Test that logging in with a bcrypt password hash upgrades it to argon2."""
    email = random_email()
    password = random_lower_string()

    # Create a bcrypt hash directly (simulating legacy password)
    bcrypt_hasher = BcryptHasher()
    bcrypt_hash = bcrypt_hasher.hash(password)
    assert bcrypt_hash.startswith("$2")  # bcrypt hashes start with $2

    user = User(email=email, hashed_password=bcrypt_hash, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    assert user.hashed_password.startswith("$2")

    request_code(client, email, password)

    db.refresh(user)

    # Verify the hash was upgraded to argon2
    assert user.hashed_password.startswith("$argon2")

    verified, updated_hash = verify_password(password, user.hashed_password)
    assert verified
    # Should not need another update since it's already argon2
    assert updated_hash is None


@pytest.mark.usefixtures("sent_emails")
def test_login_with_argon2_password_keeps_hash(client: TestClient, db: Session) -> None:
    """Test that logging in with an argon2 password hash does not update it."""
    email = random_email()
    password = random_lower_string()

    # Create an argon2 hash (current default)
    argon2_hash = get_password_hash(password)
    assert argon2_hash.startswith("$argon2")

    # Create user with argon2 hash
    user = User(email=email, hashed_password=argon2_hash, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    original_hash = user.hashed_password

    request_code(client, email, password)

    db.refresh(user)

    assert user.hashed_password == original_hash
    assert user.hashed_password.startswith("$argon2")
