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


def test_quota_blocks_the_same_cookie_or_ip_for_a_week(db: Session) -> None:
    cookie, ip = secrets.token_hex(8), f"203.0.113.{secrets.randbelow(250)}"
    guard = limits(db)
    assert guard.next_free_check(cookie, ip) is None
    guard.record_use(cookie, ip)
    assert guard.next_free_check(cookie, "198.51.100.7") is not None  # same cookie, new IP
    assert guard.next_free_check(secrets.token_hex(8), ip) is not None  # cleared cookies, same IP
    assert guard.next_free_check(secrets.token_hex(8), "198.51.100.8") is None


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
