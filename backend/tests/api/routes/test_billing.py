"""Paid plans against Postgres, with Stripe faked (no network): the webhook, the plan's checks, extra checks
sent to the meter, and the billing endpoints. Run `docker compose up -d db` and migrate first.
"""

import hashlib
import hmac
import json
import secrets
import time
from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
import stripe
from fastapi.testclient import TestClient
from sqlmodel import Session, col, delete, select

from app.api.billing import ACTIVE, Allowance, billing_period, plans, report_extra_checks
from app.api.free_check import rate_limited
from app.api.routes.billing import _webhook_client
from app.api.routes.checks import get_limits, get_llm, get_posting_date, get_usage
from app.api.billing import get_stripe, stripe_client
from app.compliance.classification import Classification
from app.compliance.extraction import Extraction
from app.core import security
from app.core.config import settings
from app.main import app
from app.models import Customer, PaidCheck, StripeEvent, User
from tests.compliance.fake_llm import FakeLLM
from tests.compliance.test_api import MemoryLimits, MemoryUsage
from tests.compliance.test_inspector import POSTING, extraction, labels

API = settings.API_V1_STR
WEBHOOK_SECRET = "whsec_test_only"
START = datetime.now(UTC).replace(microsecond=0) - timedelta(days=3)
END = START + timedelta(days=30)


# Fakes


class FakeStripe:
    """The parts of StripeClient the app uses, recording every call."""

    def __init__(self) -> None:
        self.subscriptions: dict[str, stripe.Subscription] = {}
        self.meter_events: list[dict[str, Any]] = []
        self.checkouts: list[dict[str, Any]] = []
        self.portals: list[dict[str, Any]] = []
        self.updates: list[tuple[str, dict[str, Any]]] = []
        self.meter_failures = 0
        self.v1 = SimpleNamespace(
            subscriptions=SimpleNamespace(retrieve=self.retrieve, update=self.update),
            checkout=SimpleNamespace(sessions=SimpleNamespace(create=self.create_checkout)),
            billing_portal=SimpleNamespace(sessions=SimpleNamespace(create=self.create_portal)),
            billing=SimpleNamespace(meter_events=SimpleNamespace(create=self.create_meter_event)),
        )

    def add_subscription(self, sub_id: str, customer: str, *, price: str, status: str = "active",
                         start: datetime = START, end: datetime = END, cancel: bool = False) -> None:  # fmt: skip
        self.subscriptions[sub_id] = stripe.Subscription.construct_from({
            "id": sub_id, "object": "subscription", "customer": customer, "status": status,
            "cancel_at_period_end": cancel, "cancel_at": None,
            "items": {"object": "list", "data": [
                {"id": f"si_{sub_id}_plan", "object": "subscription_item", "price": {"id": price, "object": "price"},
                 "current_period_start": int(start.timestamp()), "current_period_end": int(end.timestamp())},
                {"id": f"si_{sub_id}_extra", "object": "subscription_item",
                 "price": {"id": settings.STRIPE_PRICE_EXTRA_CHECK, "object": "price"},
                 "current_period_start": int(start.timestamp()), "current_period_end": int(end.timestamp())},
            ]},
        }, "sk_test")  # fmt: skip

    def retrieve(self, sub_id: str) -> stripe.Subscription:
        return self.subscriptions[sub_id]

    def update(self, sub_id: str, params: dict[str, Any]) -> stripe.Subscription:
        self.updates.append((sub_id, params))
        sub = self.subscriptions[sub_id]
        [change] = params["items"]
        self.add_subscription(sub_id, sub.customer, price=change["price"])
        return self.subscriptions[sub_id]

    def create_checkout(self, params: dict[str, Any]) -> Any:
        self.checkouts.append(params)
        return SimpleNamespace(url="https://checkout.stripe.com/c/pay/cs_test_1")

    def create_portal(self, params: dict[str, Any]) -> Any:
        self.portals.append(params)
        return SimpleNamespace(url="https://billing.stripe.com/p/session/test_1")

    def create_meter_event(self, params: dict[str, Any]) -> Any:
        if self.meter_failures:
            self.meter_failures -= 1
            raise stripe.APIConnectionError("network down")
        self.meter_events.append(params)
        return SimpleNamespace(identifier=params["identifier"])


@pytest.fixture
def fake_stripe(monkeypatch: pytest.MonkeyPatch) -> Generator[FakeStripe]:
    for name, value in {
        "STRIPE_SECRET_KEY": "sk_test_only", "STRIPE_WEBHOOK_SECRET": WEBHOOK_SECRET,
        "STRIPE_PRICE_STARTER": "price_starter", "STRIPE_PRICE_AGENCY": "price_agency",
        "STRIPE_PRICE_EXTRA_CHECK": "price_extra", "PLAN_CHECKS_STARTER": 3, "PLAN_EXTRA_CHECKS_MAX": 2,
    }.items():  # fmt: skip
        monkeypatch.setattr(settings, name, value)
    fake = FakeStripe()
    for dependency in (get_stripe, stripe_client, _webhook_client):
        app.dependency_overrides[dependency] = lambda: fake
    app.dependency_overrides[rate_limited] = lambda: None
    yield fake
    for dependency in (get_stripe, stripe_client, _webhook_client, rate_limited):
        app.dependency_overrides.pop(dependency, None)


def stripe_ids() -> tuple[str, str]:
    tag = secrets.token_hex(6)
    return f"cus_{tag}", f"sub_{tag}"


def make_customer(db: Session, *, plan: str | None = "starter", status: str = "active", cancel: bool = False) -> Customer:
    cus, sub = stripe_ids()
    customer = Customer(stripe_customer_id=cus, stripe_subscription_id=sub, plan=plan, subscription_status=status,
                        current_period_start=START, current_period_end=END, cancel_at_period_end=cancel)  # fmt: skip
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def make_user(db: Session, customer: Customer | None = None) -> tuple[User, dict[str, str]]:
    user = User(email=f"{secrets.token_hex(6)}@agency.example", hashed_password="x",
                customer_id=customer.id if customer else None)  # fmt: skip
    db.add(user)
    db.commit()
    db.refresh(user)
    token = security.create_access_token(user.id, expires_delta=timedelta(minutes=5))
    return user, {"Authorization": f"Bearer {token}"}


# Webhook


def post_event(client: TestClient, event: dict[str, Any], secret: str = WEBHOOK_SECRET) -> Any:
    payload = json.dumps(event)
    stamp = int(time.time())
    signature = hmac.new(secret.encode(), f"{stamp}.{payload}".encode(), hashlib.sha256).hexdigest()
    return client.post(
        f"{API}/stripe/webhook", content=payload,
        headers={"stripe-signature": f"t={stamp},v1={signature}", "content-type": "application/json"},
    )  # fmt: skip


def event(kind: str, data: dict[str, Any]) -> dict[str, Any]:
    return {"id": f"evt_{secrets.token_hex(8)}", "object": "event", "type": kind, "created": int(time.time()),
            "api_version": stripe.api_version, "data": {"object": data}}  # fmt: skip


def checkout_completed(cus: str, sub: str, email: str, reference: str | None = None) -> dict[str, Any]:
    return event("checkout.session.completed", {
        "id": f"cs_test_{secrets.token_hex(4)}", "object": "checkout.session", "mode": "subscription",
        "customer": cus, "subscription": sub, "client_reference_id": reference,
        "customer_details": {"email": email}, "payment_status": "paid", "status": "complete",
    })  # fmt: skip


@pytest.fixture
def emails(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str | None]]:
    sent: list[tuple[str, str | None]] = []
    monkeypatch.setattr("app.api.stripe_webhook.send_set_password_email", lambda email, plan: sent.append((email, plan)))
    return sent


def test_webhook_refuses_a_bad_signature(client: TestClient, fake_stripe: FakeStripe) -> None:
    cus, sub = stripe_ids()
    response = post_event(client, checkout_completed(cus, sub, "x@example.com"), secret="whsec_someone_else")
    assert response.status_code == 400
    missing = client.post(f"{API}/stripe/webhook", content="{}", headers={"content-type": "application/json"})
    assert missing.status_code == 400


def test_checkout_creates_the_account_once(client: TestClient, db: Session, fake_stripe: FakeStripe,
                                           emails: list) -> None:  # fmt: skip
    cus, sub = stripe_ids()
    fake_stripe.add_subscription(sub, cus, price="price_starter")
    email = f"Dana.{secrets.token_hex(4)}@Agency.example"
    completed = checkout_completed(cus, sub, email)

    assert post_event(client, completed).json() == {"received": True, "duplicate": False}
    assert post_event(client, completed).json() == {"received": True, "duplicate": True}  # Stripe redelivers

    customer = db.exec(select(Customer).where(Customer.stripe_customer_id == cus)).one()
    db.refresh(customer)
    assert (customer.plan, customer.subscription_status, customer.stripe_subscription_id) == ("starter", "active", sub)
    assert (customer.current_period_start, customer.current_period_end) == (START, END)
    user = db.exec(select(User).where(User.email == email.lower())).one()
    assert user.customer_id == customer.id and not user.is_superuser
    assert emails == [(email.lower(), "Starter")]  # the set-password link, sent once
    assert db.get(StripeEvent, completed["id"]) is not None


def test_checkout_with_an_unusable_email_creates_no_account(client: TestClient, db: Session, fake_stripe: FakeStripe,
                                                            emails: list) -> None:  # fmt: skip
    cus, sub = stripe_ids()
    fake_stripe.add_subscription(sub, cus, price="price_starter")
    assert post_event(client, checkout_completed(cus, sub, "someone@example.test")).status_code == 200
    assert db.exec(select(User).where(User.email == "someone@example.test")).first() is None
    assert emails == []
    customer = db.exec(select(Customer).where(Customer.stripe_customer_id == cus)).one()
    assert customer.plan == "starter"  # the subscription is still recorded, to link by hand


def test_checkout_by_a_signed_in_user_links_that_user(client: TestClient, db: Session, fake_stripe: FakeStripe,
                                                      emails: list) -> None:  # fmt: skip
    user, _ = make_user(db)
    cus, sub = stripe_ids()
    fake_stripe.add_subscription(sub, cus, price="price_agency")
    post_event(client, checkout_completed(cus, sub, "billing@other.example", reference=str(user.id)))
    db.refresh(user)
    customer = db.get(Customer, user.customer_id)
    assert customer is not None and customer.plan == "agency"
    assert emails == []  # the account already exists
    assert db.exec(select(User).where(User.email == "billing@other.example")).first() is None


def test_subscription_events_read_the_subscription_from_stripe(client: TestClient, db: Session,
                                                               fake_stripe: FakeStripe) -> None:  # fmt: skip
    customer = make_customer(db)
    sub = customer.stripe_subscription_id
    assert sub
    # The event's own copy is stale; the app reads Stripe's current one.
    fake_stripe.add_subscription(sub, customer.stripe_customer_id, price="price_starter", status="canceled")
    stale = {"id": sub, "object": "subscription", "customer": customer.stripe_customer_id, "status": "active"}
    post_event(client, event("customer.subscription.updated", stale))
    db.refresh(customer)
    assert customer.subscription_status == "canceled" and customer.subscription_status not in ACTIVE


def test_invoice_events_update_the_period_and_status(client: TestClient, db: Session, fake_stripe: FakeStripe) -> None:
    customer = make_customer(db)
    sub = customer.stripe_subscription_id
    assert sub
    renewed = END + timedelta(days=30)
    fake_stripe.add_subscription(sub, customer.stripe_customer_id, price="price_starter", start=END, end=renewed)
    invoice = {"id": "in_test", "object": "invoice", "customer": customer.stripe_customer_id,
               "parent": {"type": "subscription_details", "subscription_details": {"subscription": sub}}}  # fmt: skip
    post_event(client, event("invoice.paid", invoice))
    db.refresh(customer)
    assert (customer.current_period_start, customer.current_period_end) == (END, renewed)

    fake_stripe.add_subscription(sub, customer.stripe_customer_id, price="price_starter", status="past_due")
    post_event(client, event("invoice.payment_failed", invoice))
    db.refresh(customer)
    assert customer.subscription_status == "past_due"  # Stripe retries the card; checks keep working


def test_an_old_subscription_ending_leaves_the_current_one(client: TestClient, db: Session,
                                                           fake_stripe: FakeStripe) -> None:  # fmt: skip
    customer = make_customer(db)
    old = f"sub_old_{secrets.token_hex(4)}"
    fake_stripe.add_subscription(old, customer.stripe_customer_id, price="price_starter", status="canceled")
    post_event(client, event("customer.subscription.deleted", {"id": old, "object": "subscription"}))
    db.refresh(customer)
    assert (customer.stripe_subscription_id, customer.subscription_status) != (old, "canceled")
    assert customer.subscription_status == "active"


# The plan's checks


@pytest.fixture
def checker(fake_stripe: FakeStripe) -> Generator[tuple[FakeLLM, MemoryLimits, MemoryUsage]]:
    llm, limits, usage = FakeLLM(), MemoryLimits(per_week=0, budget=Decimal(0)), MemoryUsage()
    app.dependency_overrides[get_llm] = lambda: llm
    app.dependency_overrides[get_posting_date] = lambda: date(2026, 10, 19)
    app.dependency_overrides[get_limits] = lambda: limits
    app.dependency_overrides[get_usage] = lambda: usage
    yield llm, limits, usage
    for dependency in (get_llm, get_posting_date, get_limits, get_usage):
        app.dependency_overrides.pop(dependency, None)


def run_check(client: TestClient, llm: FakeLLM, headers: dict[str, str] | None = None) -> Any:
    llm.queue(Extraction, extraction()).queue(Classification, labels())
    return client.post(f"{API}/inspect", json={"text": POSTING, "meets_headcount_threshold": True}, headers=headers or {})


def test_customer_checks_count_against_the_plan_not_the_free_limits(
    client: TestClient, db: Session, fake_stripe: FakeStripe, checker: tuple[FakeLLM, MemoryLimits, MemoryUsage]
) -> None:
    llm, limits, usage = checker  # free limits that refuse everything: closed quota, no budget
    customer = make_customer(db)
    _, headers = make_user(db, customer)

    for _ in range(3):  # Starter's 3 checks (in this test)
        assert run_check(client, llm, headers).status_code == 200
    assert limits.uses == [] and limits.spent == 0  # the free quota and spend cap weren't touched
    assert fake_stripe.meter_events == []

    fourth = run_check(client, llm, headers)  # an extra check, billed through the meter
    assert fourth.status_code == 200
    checks = db.exec(select(PaidCheck).where(PaidCheck.customer_id == customer.id).order_by(col(PaidCheck.created_at))).all()
    assert [c.extra for c in checks] == [False, False, False, True]
    assert {c.title for c in checks} == {"Payroll Specialist"} and {c.status for c in checks} == {"not_compliant"}
    [meter] = fake_stripe.meter_events
    assert meter["event_name"] == settings.STRIPE_METER_EVENT
    assert meter["payload"] == {"stripe_customer_id": customer.stripe_customer_id, "value": "1"}
    assert meter["identifier"] == str(checks[3].id)
    db.refresh(checks[3])
    assert checks[3].reported_at is not None

    assert {e["plan"] for e in usage.events if e["kind"] == "check"} == {"starter"}
    assert all(e.get("visitor") is None for e in usage.events)

    billing = client.get(f"{API}/billing", headers=headers).json()
    assert (billing["plan"], billing["checks_included"], billing["checks_used"], billing["extra_checks"]) == ("starter", 3, 4, 1)

    run_check(client, llm, headers)  # the second extra check, the last one allowed in this test
    refused = run_check(client, llm, headers)
    assert refused.status_code == 429 and refused.json()["detail"]["reason"] == "plan_limit"


def test_visitors_and_lapsed_customers_keep_the_free_rules(
    client: TestClient, db: Session, fake_stripe: FakeStripe, checker: tuple[FakeLLM, MemoryLimits, MemoryUsage]
) -> None:
    llm, limits, _ = checker
    assert run_check(client, llm).json()["detail"]["reason"] == "quota"  # a visitor: the closed free quota
    _, headers = make_user(db, make_customer(db, status="canceled"))
    assert run_check(client, llm, headers).json()["detail"]["reason"] == "quota"
    _, headers = make_user(db)  # signed in with no plan, such as an admin
    assert run_check(client, llm, headers).json()["detail"]["reason"] == "quota"
    assert fake_stripe.meter_events == []


def test_applying_fixes_records_the_final_status(
    client: TestClient, db: Session, fake_stripe: FakeStripe, checker: tuple[FakeLLM, MemoryLimits, MemoryUsage]
) -> None:
    from app.compliance.refiner import _Rewrite

    llm, limits, _ = checker
    customer = make_customer(db)
    _, headers = make_user(db, customer)
    check = run_check(client, llm, headers).json()
    llm.queue(_Rewrite, {"sentence": "2+ years of payroll experience"})
    llm.queue(Classification, {"canadian_experience": [{"sentence": 4, "label": "ok", "reason": "r"}], "vacancy": [], "ai": []})
    client.post(f"{API}/refine", json={"check_id": check["check_id"]})
    final = client.post(f"{API}/patches/accept", json={"check_id": check["check_id"], "decisions": []}).json()
    row = db.exec(select(PaidCheck).where(PaidCheck.check_id == check["check_id"])).one()
    db.refresh(row)
    assert (row.status, row.final_status) == ("not_compliant", final["report"]["status"])
    assert limits.spent == 0  # a customer's rewrite doesn't use the free spend cap

    history = client.get(f"{API}/billing/checks", headers=headers).json()
    assert history["count"] == 1 and history["data"][0]["title"] == "Payroll Specialist"
    assert set(history["data"][0]) == {"id", "created_at", "title", "status", "final_status", "extra"}


def test_failed_meter_reports_are_retried(db: Session, fake_stripe: FakeStripe) -> None:
    customer = make_customer(db)
    checks = [PaidCheck(customer_id=customer.id, check_id=secrets.token_hex(4), status="compliant", extra=True)
              for _ in range(2)]  # fmt: skip
    db.add_all(checks)
    db.commit()
    fake_stripe.meter_failures = 1
    assert report_extra_checks(fake_stripe, db, customer.id) == 0  # type: ignore[arg-type]
    assert report_extra_checks(fake_stripe, db, customer.id) == 2  # type: ignore[arg-type]
    assert report_extra_checks(fake_stripe, db, customer.id) == 0  # type: ignore[arg-type]
    assert sorted(e["identifier"] for e in fake_stripe.meter_events) == sorted(str(c.id) for c in checks)


def test_the_period_rolls_over_when_the_renewal_is_late() -> None:
    customer = Customer(stripe_customer_id="cus_x", current_period_start=START, current_period_end=END)
    assert billing_period(customer, START + timedelta(days=1)) == (START, END)
    assert billing_period(customer, END + timedelta(hours=1)) == (END, END + (END - START))
    allowance = Allowance(plans()["starter"], START, END, used=55)
    assert allowance.extra == 5


# Billing endpoints


def test_checkout_is_off_until_stripe_is_set_up(client: TestClient) -> None:
    response = client.post(f"{API}/billing/checkout", json={"plan": "starter"})
    assert response.status_code == 503


def test_checkout_starts_a_subscription_with_the_extra_check_price(client: TestClient, db: Session,
                                                                   fake_stripe: FakeStripe) -> None:  # fmt: skip
    response = client.post(f"{API}/billing/checkout", json={"plan": "agency"})
    assert response.json() == {"url": "https://checkout.stripe.com/c/pay/cs_test_1"}
    [params] = fake_stripe.checkouts
    assert params["mode"] == "subscription"
    assert params["line_items"] == [{"price": "price_agency", "quantity": 1}, {"price": "price_extra"}]
    assert params["consent_collection"] == {"terms_of_service": "required"}
    assert "/terms)" in params["custom_text"]["terms_of_service_acceptance"]["message"]
    assert "customer" not in params and "client_reference_id" not in params

    customer = make_customer(db, status="canceled")  # coming back: same Stripe customer
    user, headers = make_user(db, customer)
    client.post(f"{API}/billing/checkout", json={"plan": "starter"}, headers=headers)
    assert fake_stripe.checkouts[-1]["customer"] == customer.stripe_customer_id
    assert fake_stripe.checkouts[-1]["client_reference_id"] == str(user.id)

    _, active = make_user(db, make_customer(db))
    assert client.post(f"{API}/billing/checkout", json={"plan": "agency"}, headers=active).status_code == 409


def test_portal_and_plan_change(client: TestClient, db: Session, fake_stripe: FakeStripe) -> None:
    customer = make_customer(db)
    assert customer.stripe_subscription_id
    fake_stripe.add_subscription(customer.stripe_subscription_id, customer.stripe_customer_id, price="price_starter")
    _, headers = make_user(db, customer)

    portal = client.post(f"{API}/billing/portal", headers=headers).json()
    assert portal["url"].startswith("https://billing.stripe.com/")
    assert fake_stripe.portals == [{"customer": customer.stripe_customer_id, "return_url": f"{settings.FRONTEND_HOST}/"}]

    changed = client.post(f"{API}/billing/plan", json={"plan": "agency"}, headers=headers).json()
    assert (changed["plan"], changed["checks_included"]) == ("agency", settings.PLAN_CHECKS_AGENCY)
    [(sub, params)] = fake_stripe.updates
    assert params["items"] == [{"id": f"si_{sub}_plan", "price": "price_agency"}]
    assert client.post(f"{API}/billing/plan", json={"plan": "agency"}, headers=headers).status_code == 409

    _, no_plan = make_user(db)
    assert client.post(f"{API}/billing/portal", headers=no_plan).status_code == 404
    assert client.get(f"{API}/billing", headers=no_plan).json()["plan"] is None


def test_a_paying_user_cancels_before_deleting_the_account(client: TestClient, db: Session) -> None:
    customer = make_customer(db)
    user, headers = make_user(db, customer)
    assert client.delete(f"{API}/users/me", headers=headers).status_code == 409
    customer.cancel_at_period_end = True
    db.add(customer)
    db.commit()
    assert client.delete(f"{API}/users/me", headers=headers).status_code == 200


@pytest.fixture(autouse=True, scope="module")
def clean_up(db: Session) -> Generator[None]:
    yield
    db.execute(delete(PaidCheck))
    db.execute(delete(StripeEvent))
    for user in db.exec(select(User).where(col(User.customer_id).is_not(None))).all():
        db.delete(user)
    db.execute(delete(Customer))
    db.commit()
