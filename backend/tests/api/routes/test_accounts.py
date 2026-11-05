"""Accounts without plans: sign-up only when the server opens it, every feature for a signed-in user, and the
optional limit on each account's checks. Run `docker compose up -d db` and migrate first."""

import secrets
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, func, select

from app.api.routes import signup
from app.core.config import settings
from app.models import User
from tests.api.routes.test_workspaces import check, customer_headers, llm  # noqa: F401 (fixture)
from tests.compliance.fake_llm import FakeLLM

API = settings.API_V1_STR


def address() -> str:
    return f"{secrets.token_hex(6)}@agency.example"


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """The sign-up emails, instead of sending them."""
    mail: list[tuple[str, str]] = []
    monkeypatch.setattr(signup, "send_signup_email", lambda email: mail.append(("new", email)))
    monkeypatch.setattr(signup, "send_existing_account_email", lambda email: mail.append(("existing", email)))
    monkeypatch.setattr(signup, "_signups", signup.RateLimiter(100, window_seconds=3600))
    return mail


def test_sign_up_is_closed_by_default(client: TestClient, db: Session, sent: list[Any]) -> None:
    email = address()
    response = client.post(f"{API}/signup", json={"email": email})
    assert response.status_code == 403 and response.json()["detail"]["reason"] == "signup_closed"
    assert db.exec(select(User).where(col(User.email) == email)).first() is None and sent == []


def test_open_sign_up_makes_a_user_and_emails_the_link(
    client: TestClient, db: Session, sent: list[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "SIGNUP_OPEN", True)
    email = address()
    response = client.post(f"{API}/signup", json={"email": email.upper()})
    assert response.status_code == 202
    user = db.exec(select(User).where(col(User.email) == email)).one()
    assert user.customer_id is None  # the account is made on the first signed-in request
    assert sent == [("new", email)]

    again = client.post(f"{API}/signup", json={"email": email})  # the same answer: nothing tells it apart
    assert again.status_code == 202 and again.json() == response.json()
    assert sent[-1] == ("existing", user.email)
    assert db.exec(select(func.count()).select_from(User).where(col(User.email) == email)).one() == 1


def test_the_account_reports_its_checks_and_the_server_settings(
    client: TestClient, db: Session, llm: FakeLLM, monkeypatch: pytest.MonkeyPatch  # noqa: F811
) -> None:
    headers = customer_headers(db)
    check(client, llm, headers)
    account = client.get(f"{API}/account", headers=headers).json()
    assert account == {"checks_used": 1, "checks_limit": None, "signup_open": False}
    monkeypatch.setattr(settings, "ACCOUNT_CHECKS_PER_30_DAYS", 10)
    assert client.get(f"{API}/account", headers=headers).json()["checks_limit"] == 10
    assert client.get(f"{API}/account").status_code == 401


def test_the_account_limit_stops_checks(
    client: TestClient, db: Session, llm: FakeLLM, monkeypatch: pytest.MonkeyPatch  # noqa: F811
) -> None:
    monkeypatch.setattr(settings, "ACCOUNT_CHECKS_PER_30_DAYS", 2)
    headers = customer_headers(db)
    check(client, llm, headers)
    check(client, llm, headers)
    refused = check(client, llm, headers, status=429)
    assert refused["detail"]["reason"] == "account_limit"
    assert "2 checks for the last 30 days" in refused["detail"]["message"]
    other = customer_headers(db)  # each account has its own
    check(client, llm, other)
