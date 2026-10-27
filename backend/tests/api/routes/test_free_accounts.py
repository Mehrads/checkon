"""Free accounts against Postgres: signing up, the free plan's checks, what stays with the paid plans, and a free
account that subscribes keeping its history. Run `docker compose up -d db` and migrate first.
"""

import secrets
from collections.abc import Generator
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, delete, func, select

from app.api.billing import free_customer
from app.api.routes import signup
from app.api.routes.checks import get_limits, get_llm, get_posting_date, get_usage
from app.compliance.classification import Classification
from app.compliance.extraction import Extraction
from app.core.config import settings
from app.main import app
from app.models import Customer, OutreachReport, PaidCheck, User, get_datetime_utc
from tests.api.routes.test_billing import (  # noqa: F401 (fixtures)
    FakeStripe,
    checkout_completed,
    emails,
    fake_stripe,
    make_user,
    post_event,
    run_check,
    stripe_ids,
)
from tests.compliance.fake_llm import FakeLLM
from tests.compliance.test_api import MemoryLimits, MemoryUsage, site  # noqa: F401 (fixture)
from tests.compliance.test_inspector import extraction, labels

API = settings.API_V1_STR


def address() -> str:
    return f"hr+{secrets.token_hex(4)}@employer.example"


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, Any]]:
    """The sign-up emails, instead of sending them."""
    mail: list[tuple[str, Any]] = []
    monkeypatch.setattr(signup, "send_free_account_email", lambda email, report: mail.append(("new", email, report)))
    monkeypatch.setattr(signup, "send_existing_account_email", lambda email: mail.append(("existing", email)))
    monkeypatch.setattr(signup, "_signups", signup.RateLimiter(100, window_seconds=3600))
    return mail


def make_free_user(db: Session) -> tuple[User, dict[str, str]]:
    customer = free_customer(address(), get_datetime_utc())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return make_user(db, customer)


@pytest.fixture
def free_checker(monkeypatch: pytest.MonkeyPatch) -> Generator[tuple[FakeLLM, MemoryLimits]]:
    """Two free checks per account, and free limits with a closed weekly quota but money left for the day."""
    monkeypatch.setattr(settings, "PLAN_CHECKS_FREE", 2)
    llm, limits = FakeLLM(), MemoryLimits(per_week=0, budget=Decimal(5))
    app.dependency_overrides[get_llm] = lambda: llm
    app.dependency_overrides[get_posting_date] = lambda: date(2026, 10, 19)
    app.dependency_overrides[get_limits] = lambda: limits
    app.dependency_overrides[get_usage] = MemoryUsage
    yield llm, limits
    for dependency in (get_llm, get_posting_date, get_limits, get_usage):
        app.dependency_overrides.pop(dependency, None)


def test_signing_up_makes_a_free_account_and_emails_the_link(
    client: TestClient, db: Session, sent: list[tuple[str, Any]]
) -> None:
    email = address()
    response = client.post(f"{API}/signup", json={"email": email.upper()})
    assert response.status_code == 202
    user = db.exec(select(User).where(col(User.email) == email)).one()
    customer = db.get(Customer, user.customer_id)
    assert customer is not None and (customer.plan, customer.subscription_status) == ("free", "active")
    assert customer.stripe_customer_id is None and not customer.complimentary
    assert sent == [("new", email, None)]

    again = client.post(f"{API}/signup", json={"email": email})  # the same answer: nothing tells it apart
    assert again.status_code == 202 and again.json() == response.json()
    assert sent[-1] == ("existing", user.email)
    assert db.exec(select(func.count()).select_from(User).where(col(User.email) == email)).one() == 1


def test_signing_up_from_a_report_brings_the_visitor_back_to_it(
    client: TestClient, db: Session, sent: list[tuple[str, Any]]
) -> None:
    report = OutreachReport(token=secrets.token_urlsafe(24), company="Acme", url="https://jobs.lever.co/acme",
                            found=3, outside_ontario=0)  # fmt: skip
    db.add(report)
    db.commit()
    email = address()
    client.post(f"{API}/signup", json={"email": email, "report": report.token})
    assert sent == [("new", email, (report.token, "Acme"))]
    client.post(f"{API}/signup", json={"email": address(), "report": "no-such-report"})
    assert sent[-1][2] is None


def test_the_email_link_sets_the_password_and_comes_back_to_the_report(monkeypatch: pytest.MonkeyPatch) -> None:
    mail: list[tuple[Any, str, str]] = []
    monkeypatch.setattr(signup, "_send", lambda email, to, link: mail.append((email, to, link)))
    signup.send_free_account_email("hr@acme.example", ("tok123", "Acme"))
    [(email, to, link)] = mail
    assert to == "hr@acme.example" and "new=1" in link and "next=%2Freport%2Ftok123%3Fsave%3D1" in link
    html = email.html_content.replace("<!-- -->", "")  # React Email's markers between text and values
    assert "Acme&#x27;s report is waiting" in html or "Acme's report is waiting" in html
    assert f"{settings.PLAN_CHECKS_FREE} checks every 30 days" in html


@pytest.mark.usefixtures("sent")
def test_sign_ups_are_limited_per_address(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(signup, "_signups", signup.RateLimiter(2, window_seconds=3600))
    for _ in range(2):
        assert client.post(f"{API}/signup", json={"email": address()}).status_code == 202
    refused = client.post(f"{API}/signup", json={"email": address()})
    assert refused.status_code == 429 and refused.json()["detail"]["reason"] == "rate_limit"


def test_a_free_account_has_its_checks_and_history_but_not_the_paid_features(
    client: TestClient, db: Session, free_checker: tuple[FakeLLM, MemoryLimits]
) -> None:
    llm, limits = free_checker
    user, headers = make_free_user(db)
    for _ in range(2):
        assert run_check(client, llm, headers).status_code == 200
    assert limits.uses == []  # not the visitor's weekly check
    used_up = run_check(client, llm, headers)
    assert used_up.status_code == 429 and used_up.json()["detail"]["reason"] == "free_account_limit"
    checks = db.exec(select(PaidCheck).where(PaidCheck.customer_id == user.customer_id)).all()
    assert len(checks) == 2 and not any(check.extra for check in checks)

    billing = client.get(f"{API}/billing", headers=headers).json()
    assert (billing["plan"], billing["plan_name"], billing["checks_included"], billing["checks_used"]) == ("free", "Free", 2, 2)
    assert billing["extra_checks_max"] == 0 and not billing["has_billing"]
    assert len(client.get(f"{API}/billing/checks", headers=headers).json()["data"]) == 2

    assert client.get(f"{API}/workspaces/", headers=headers).status_code == 403
    audit = client.post(f"{API}/audits/preview", json={"url": "https://jobs.lever.co/acme"}, headers=headers)
    assert audit.status_code == 403
    assert client.get(f"{API}/archive/", headers=headers).status_code == 403
    assert client.post(f"{API}/billing/plan", json={"plan": "agency"}, headers=headers).status_code == 409


@pytest.mark.usefixtures("site")
def test_an_account_checks_a_linked_posting_longer_than_a_paste(
    client: TestClient, db: Session, free_checker: tuple[FakeLLM, MemoryLimits]
) -> None:
    llm, _ = free_checker
    long_page = {"url": "https://jobs.example.com/long", "meets_headcount_threshold": True}  # 9,600 characters
    for _ in range(3):  # the made-up page doesn't hold the scripted quotes, so extraction is retried
        llm.queue(Extraction, extraction()).queue(Classification, labels())
    _, headers = make_free_user(db)
    response = client.post(f"{API}/inspect", json=long_page, headers=headers)
    assert not (response.status_code == 422 and response.json()["detail"]["reason"] == "too_long")
    visitor = client.post(f"{API}/inspect", json=long_page)  # the free check keeps the paste's limit
    assert visitor.json()["detail"]["reason"] in ("too_long", "quota")


def test_free_accounts_stop_with_the_free_checks_when_the_day_s_budget_is_spent(
    client: TestClient, db: Session, free_checker: tuple[FakeLLM, MemoryLimits]
) -> None:
    llm, limits = free_checker
    limits.budget = Decimal(0)
    _, headers = make_free_user(db)
    paused = run_check(client, llm, headers)
    assert paused.status_code == 503 and paused.json()["detail"]["reason"] == "paused"


def test_a_free_account_can_be_deleted_any_time_and_takes_its_data_along(client: TestClient, db: Session) -> None:
    user, headers = make_free_user(db)
    customer_id = user.customer_id
    db.add(PaidCheck(customer_id=customer_id, user_id=user.id, check_id="free-del", title="Payroll Specialist",
                     status="not_compliant"))  # fmt: skip
    db.add(OutreachReport(token=secrets.token_urlsafe(24), company="Acme", url="https://jobs.lever.co/acme",
                          found=1, outside_ontario=0, customer_id=customer_id))  # fmt: skip
    db.commit()
    assert client.delete(f"{API}/users/me", headers=headers).status_code == 200
    db.expire_all()
    assert db.get(Customer, customer_id) is None  # never billed: nothing to keep for tax records
    assert db.exec(select(PaidCheck).where(PaidCheck.customer_id == customer_id)).first() is None
    assert db.exec(select(OutreachReport).where(OutreachReport.customer_id == customer_id)).first() is None


def test_a_free_account_that_subscribes_keeps_its_checks_and_reports(
    client: TestClient, db: Session, fake_stripe: FakeStripe, emails: list  # noqa: F811
) -> None:
    user, _ = make_free_user(db)
    free_id = user.customer_id
    db.add(PaidCheck(customer_id=free_id, user_id=user.id, check_id="free-1", title="Payroll Specialist",
                     status="not_compliant"))  # fmt: skip
    report = OutreachReport(token=secrets.token_urlsafe(24), company="Acme", url="https://jobs.lever.co/acme",
                            found=1, outside_ontario=0, customer_id=free_id)  # fmt: skip
    db.add(report)
    db.commit()

    cus, sub = stripe_ids()
    fake_stripe.add_subscription(sub, cus, price="price_starter")
    assert post_event(client, checkout_completed(cus, sub, user.email, reference=str(user.id))).status_code == 200

    db.expire_all()
    paying = db.get(Customer, db.get(User, user.id).customer_id)  # type: ignore[union-attr]
    assert paying is not None and (paying.plan, paying.stripe_customer_id) == ("starter", cus)
    assert db.get(Customer, free_id) is None
    assert [c.check_id for c in db.exec(select(PaidCheck).where(PaidCheck.customer_id == paying.id)).all()] == ["free-1"]
    assert db.get(OutreachReport, report.id).customer_id == paying.id  # type: ignore[union-attr]
    assert emails == []


def test_checkout_is_open_to_a_free_account(client: TestClient, db: Session, fake_stripe: FakeStripe) -> None:  # noqa: F811
    _, headers = make_free_user(db)
    response = client.post(f"{API}/billing/checkout", json={"plan": "starter"}, headers=headers)
    assert response.status_code == 200
    assert fake_stripe.checkouts[-1]["customer_email"].endswith("@agency.example")


@pytest.fixture(autouse=True, scope="module")
def clean_up(db: Session) -> Generator[None]:
    yield
    db.execute(delete(OutreachReport))
    db.execute(delete(PaidCheck))
    for user in db.exec(select(User).where(col(User.customer_id).is_not(None))).all():
        db.delete(user)
    db.execute(delete(Customer))
    db.commit()
