"""Our complimentary test account (`python -m app.test_account`): a plan with nothing billed, against Postgres."""

import secrets
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from app.api.routes.stats import compute_stats
from app.core import security
from app.core.config import settings
from app.models import Customer, PaidCheck, UsageEvent, User
from app.test_account import Refused, end_test_account, main, make_test_account
from tests.api.routes.test_billing import (  # noqa: F401 (fixtures)
    FakeStripe,
    MemoryLimits,
    MemoryUsage,
    checker,
    fake_stripe,
    make_customer,
    make_user,
    run_check,
)
from tests.compliance.fake_llm import FakeLLM

API = settings.API_V1_STR


def email() -> str:
    return f"tester+{secrets.token_hex(4)}@checkon.example"


def headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {security.create_access_token(user.id, expires_delta=timedelta(minutes=5))}"}


@pytest.fixture
def emails(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str | None]]:
    sent: list[tuple[str, str | None]] = []
    monkeypatch.setattr("app.test_account.send_set_password_email", lambda to, plan: sent.append((to, plan)))
    return sent


def test_the_command_creates_the_account_once_and_switches_its_plan(
    db: Session, emails: list[tuple[str, str | None]], monkeypatch: pytest.MonkeyPatch
) -> None:
    address = email()
    monkeypatch.setattr(sys, "argv", ["test_account", address.upper()])
    main()
    user = db.exec(select(User).where(col(User.email) == address)).one()
    customer = db.get(Customer, user.customer_id)
    assert customer is not None and customer.complimentary
    assert (customer.plan, customer.subscription_status, customer.stripe_customer_id) == ("agency", "active", None)
    assert emails == [(address, "Agency")]

    monkeypatch.setattr(sys, "argv", ["test_account", address, "--plan", "starter"])
    main()  # the same user and customer; no second email
    db.refresh(customer)
    assert customer.plan == "starter" and emails == [(address, "Agency")]
    assert len(db.exec(select(User).where(col(User.email) == address)).all()) == 1

    monkeypatch.setattr(sys, "argv", ["test_account", address, "--end"])
    main()
    db.refresh(customer)
    assert customer.subscription_status == "canceled"
    _, customer, created = make_test_account(db, address)  # back on
    assert customer.subscription_status == "active" and not created


def test_a_paying_customer_or_an_admin_is_never_a_test_account(db: Session) -> None:
    payer, _ = make_user(db, make_customer(db))
    with pytest.raises(Refused, match="pays through Stripe"):
        make_test_account(db, payer.email)
    admin = db.exec(select(User).where(col(User.email) == settings.FIRST_SUPERUSER)).one()
    with pytest.raises(Refused, match="admin"):
        make_test_account(db, admin.email)
    with pytest.raises(Refused, match="isn't an email"):
        make_test_account(db, "not an email")
    with pytest.raises(Refused, match="no test account"):
        end_test_account(db, payer.email)


def test_its_checks_count_against_the_plan_and_nothing_goes_to_stripe(
    client: TestClient, db: Session, fake_stripe: FakeStripe, checker: tuple[FakeLLM, MemoryLimits, MemoryUsage]  # noqa: F811
) -> None:
    llm, limits, _ = checker
    user, customer, _ = make_test_account(db, email(), "starter")
    for _ in range(5):  # Starter's 3 checks in these tests, then the 2 extra ones
        assert run_check(client, llm, headers(user)).status_code == 200
    rows = db.exec(select(PaidCheck).where(PaidCheck.customer_id == customer.id)).all()
    assert len(rows) == 5 and sum(row.extra for row in rows) == 2
    assert fake_stripe.meter_events == []  # extra checks are never billed
    assert limits.uses == [] and limits.spent == 0
    assert run_check(client, llm, headers(user)).json()["detail"]["reason"] == "plan_limit"


def test_billing_shows_a_test_account_and_switches_plan_without_stripe(client: TestClient, db: Session) -> None:
    user, _, _ = make_test_account(db, email())
    billing = client.get(f"{API}/billing", headers=headers(user)).json()
    assert (billing["plan"], billing["complimentary"], billing["has_billing"]) == ("agency", True, False)

    portal = client.post(f"{API}/billing/portal", headers=headers(user))
    assert portal.status_code in (409, 503)  # 503 when Stripe isn't set up here; 409 once it is
    switched = client.post(f"{API}/billing/plan", json={"plan": "starter"}, headers=headers(user))
    assert switched.status_code == 200, switched.text  # Stripe isn't set up in tests: no call needed
    assert switched.json()["plan"] == "starter"


@pytest.mark.usefixtures("fake_stripe")
def test_the_portal_explains_there_is_nothing_to_bill(client: TestClient, db: Session) -> None:
    user, _, _ = make_test_account(db, email())
    portal = client.post(f"{API}/billing/portal", headers=headers(user))
    assert portal.status_code == 409 and "complimentary test account" in portal.json()["detail"]


def test_a_test_account_can_be_deleted_without_cancelling(client: TestClient, db: Session) -> None:
    user, _, _ = make_test_account(db, email())
    response = client.delete(f"{API}/users/me", headers=headers(user))
    assert response.status_code == 200, response.text


def test_stats_leave_out_the_test_account(db: Session) -> None:
    now = datetime(2026, 10, 23, 15, tzinfo=UTC)
    before = compute_stats(db, now).totals
    _, test, _ = make_test_account(db, email())
    real = make_customer(db)
    for customer, check_id in ((test, f"t-{secrets.token_hex(4)}"), (real, f"r-{secrets.token_hex(4)}")):
        db.add(PaidCheck(customer_id=customer.id, check_id=check_id, title="Payroll", status="compliant"))
        db.add(UsageEvent(kind="check", check_id=check_id, plan="agency", status="compliant", usd=Decimal("0.01"), at=now))
    db.commit()
    after = compute_stats(db, now).totals
    assert after.customers == before.customers + 1  # the real one only
    assert after.paid_checks == before.paid_checks + 1
