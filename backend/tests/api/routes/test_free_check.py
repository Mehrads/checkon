"""Free-check limits and research hooks against Postgres (run `docker compose up -d db` and migrate first)."""

import secrets
from collections.abc import Generator
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.api.free_check import PostgresLimits, rate_limited
from app.core.config import settings
from app.main import app
from app.models import CustomRequest, Feedback, FreeCheckSpend, ResearchAnswer

API = settings.API_V1_STR
DAY = date(2026, 10, 19)


@pytest.fixture(autouse=True)
def no_rate_limit() -> Generator[None]:
    app.dependency_overrides[rate_limited] = lambda: None
    yield
    app.dependency_overrides.pop(rate_limited, None)


def limits(db: Session, per_week: int = 1, cap: Decimal = Decimal(5)) -> PostgresLimits:
    return PostgresLimits(db, DAY, per_week, cap, settings.SECRET_KEY)


def new_ip() -> str:
    """An address no earlier run used: the quota rows stay in a local test database for a week."""
    return f"2001:db8::{secrets.token_hex(2)}:{secrets.token_hex(2)}"


def test_quota_blocks_the_same_cookie_or_ip_for_a_week(db: Session) -> None:
    cookie, ip = secrets.token_hex(8), new_ip()
    guard = limits(db)
    assert guard.next_free_check(cookie, ip) is None
    guard.record_use(cookie, ip)
    assert guard.next_free_check(cookie, new_ip()) is not None  # same cookie, new IP
    assert guard.next_free_check(secrets.token_hex(8), ip) is not None  # cleared cookies, same IP
    assert guard.next_free_check(secrets.token_hex(8), new_ip()) is None


def test_the_sample_audit_has_its_own_weekly_quota(db: Session) -> None:
    cookie, ip = secrets.token_hex(8), new_ip()
    sample = PostgresLimits(db, DAY, 1, Decimal(5), settings.SECRET_KEY, scope="sample-")
    limits(db).record_use(cookie, ip)  # the week's free check
    assert sample.next_free_check(cookie, ip) is None  # doesn't use up the sample audit
    sample.record_use(cookie, ip)
    assert sample.next_free_check(cookie, ip) is not None


def test_quota_stores_hashes_not_raw_values(db: Session) -> None:
    cookie, ip = secrets.token_hex(8), "203.0.113.99"
    limits(db).record_use(cookie, ip)
    from app.models import FreeCheckUse

    keys = [row.key_hash for row in db.exec(select(FreeCheckUse)).all()]
    assert all(cookie not in key and ip not in key and len(key) == 64 for key in keys)


def test_spend_adds_up_and_closes_the_budget(db: Session) -> None:
    db.exec(delete(FreeCheckSpend).where(FreeCheckSpend.day == DAY))
    db.commit()
    guard = limits(db, cap=Decimal("0.01"))
    guard.add_spend(Decimal("0.006"))
    assert guard.budget_left()
    guard.add_spend(Decimal("0.006"))
    assert db.get(FreeCheckSpend, DAY).usd == Decimal("0.012")
    assert not guard.budget_left()


def test_research_answer_is_stored(client: TestClient, db: Session) -> None:
    check_id = secrets.token_hex(8)
    body = {"check_id": check_id, "question_id": "hr_system", "answer": "BambooHR"}
    assert client.post(f"{API}/research/answer", json=body).status_code == 201
    row = db.exec(select(ResearchAnswer).where(ResearchAnswer.check_id == check_id)).one()
    assert (row.question_id, row.answer) == ("hr_system", "BambooHR")


def test_research_answer_must_be_one_of_the_options(client: TestClient) -> None:
    body = {"check_id": "x", "question_id": "hr_system", "answer": "Something else entirely"}
    assert client.post(f"{API}/research/answer", json=body).status_code == 422


def test_custom_request_is_stored(client: TestClient, db: Session) -> None:
    email = f"{secrets.token_hex(4)}@agency.example"
    body = {"hr_system": "BambooHR", "postings_per_month": "11–50", "wants": "Check every new opening", "email": email}
    assert client.post(f"{API}/requests", json=body).status_code == 201
    assert db.exec(select(CustomRequest).where(CustomRequest.email == email)).one().hr_system == "BambooHR"


def test_custom_request_needs_a_valid_email(client: TestClient) -> None:
    body = {"hr_system": "BambooHR", "postings_per_month": "1–2", "wants": "x", "email": "not-an-email"}
    assert client.post(f"{API}/requests", json=body).status_code == 422


def test_feedback_keeps_no_posting_text_without_consent(client: TestClient, db: Session) -> None:
    check_id = secrets.token_hex(8)
    body = {"check_id": check_id, "target_kind": "finding", "target_id": "ON-CEX-01", "rating": "down",
            "reason": "wrong_rule", "comment": "This is a licence, not experience."}  # fmt: skip
    assert client.post(f"{API}/feedback", json=body).status_code == 201
    row = db.exec(select(Feedback).where(Feedback.check_id == check_id)).one()
    assert (row.rating, row.reason, row.posting_text, row.review_status) == ("down", "wrong_rule", None, "new")


def test_contact_message_is_saved(client: TestClient, db: Session) -> None:
    from app.models import ContactMessage

    email = f"{secrets.token_hex(4)}@agency.example"
    body = {"name": "Dana", "email": email, "company": "Agency Inc.", "interest": "agency", "message": "Pricing for 12 clients?"}
    assert client.post(f"{API}/contact", json=body).status_code == 201
    row = db.exec(select(ContactMessage).where(ContactMessage.email == email)).one()
    assert (row.interest, row.company) == ("agency", "Agency Inc.")


def test_contact_message_is_emailed_to_the_owner(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[dict] = []
    monkeypatch.setattr(settings, "CONTACT_EMAIL", "owner@example.com")
    monkeypatch.setattr(settings, "SMTP_HOST", "localhost")
    monkeypatch.setattr(settings, "EMAILS_FROM_EMAIL", "info@example.com")
    monkeypatch.setattr("app.utils.send_email", lambda **kwargs: sent.append(kwargs))
    body = {"name": "Sam <b>", "email": "sam@example.com", "interest": "custom", "message": "We use BambooHR.\nCan you connect it?"}
    assert client.post(f"{API}/contact", json=body).status_code == 201
    [email] = sent
    assert email["email_to"] == "owner@example.com"
    assert email["subject"] == "CheckON: Custom setup enquiry from Sam <b>"
    assert "Sam &lt;b&gt;" in email["html_content"] and "BambooHR.<br>Can you" in email["html_content"]


def test_contact_needs_a_valid_email(client: TestClient) -> None:
    body = {"name": "Dana", "email": "nope", "interest": "starter", "message": "Hi"}
    assert client.post(f"{API}/contact", json=body).status_code == 422
