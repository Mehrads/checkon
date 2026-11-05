"""Company profiles and client workspaces against Postgres, with a scripted LLM (no network): the profile fills
a customer's check, so its questions and the employer-size search are skipped; Agency's checks and history are
scoped to a client workspace and share one allowance; Starter has one profile and no workspaces. Run
`docker compose up -d db` and migrate first.
"""

import secrets
from collections.abc import Generator
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, delete, select

from app.api.free_check import rate_limited
from app.api.routes.checks import (
    get_limits,
    get_llm,
    get_posting_date,
    get_sizes,
    get_usage,
)
from app.compliance.classification import Classification
from app.compliance.employer import EmployerSize
from app.compliance.extraction import Extraction
from app.compliance.refiner import _Rewrite
from app.compliance.wording import load_wording
from app.core.config import settings
from app.main import app
from app.models import Customer, PaidCheck, User, Workspace
from tests.compliance.fake_llm import FakeLLM
from tests.compliance.test_api import MemoryLimits, MemoryUsage
from tests.compliance.test_employer import MemorySizes
from tests.compliance.test_inspector import POSTING, extraction, labels
from tests.utils.accounts import make_customer, make_user

API = settings.API_V1_STR
SIZE = {"found": True, "total_employees_min": 900, "total_employees_max": 1100, "ontario_employees_min": None,
        "ontario_employees_max": None, "summary": "about 1,000 employees", "source_url": "https://example.com"}  # fmt: skip


@pytest.fixture
def llm() -> Generator[FakeLLM]:
    fake, limits = FakeLLM(), MemoryLimits(per_week=0, budget=Decimal(0))  # free checks are all refused
    app.dependency_overrides[get_llm] = lambda: fake
    app.dependency_overrides[get_posting_date] = lambda: date(2026, 10, 19)
    app.dependency_overrides[get_limits] = lambda: limits
    app.dependency_overrides[get_usage] = MemoryUsage
    app.dependency_overrides[get_sizes] = MemorySizes
    app.dependency_overrides[rate_limited] = lambda: None
    yield fake
    for dependency in (get_llm, get_posting_date, get_limits, get_usage, get_sizes, rate_limited):
        app.dependency_overrides.pop(dependency, None)


def customer_headers(db: Session) -> dict[str, str]:
    return make_user(db, make_customer(db))[1]


def check(
    client: TestClient, llm: FakeLLM, headers: dict[str, str], employer: str | None = None,
    workspace: str | None = None, status: int = 200,
) -> dict[str, Any]:  # fmt: skip
    """A check of the sample posting, which has no AI statement and names `employer` in its last line."""
    text = f"{POSTING}\nJoin {employer}.\n" if employer else POSTING
    llm.queue(Extraction, extraction(employer=employer)).queue(Classification, labels())
    response = client.post(f"{API}/inspect", json={"text": text, "workspace_id": workspace}, headers=headers)
    assert response.status_code == status, response.text
    return response.json()


def result(check: dict[str, Any], rule: str) -> dict[str, Any]:
    return next(r for r in check["report"]["results"] if r["rule"] == rule)


def save_profile(client: TestClient, headers: dict[str, str], **fields: Any) -> dict[str, Any]:
    current = client.get(f"{API}/workspaces/current", headers=headers).json()
    response = client.patch(f"{API}/workspaces/{current['id']}", json=fields, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_the_profile_answers_the_check_instead_of_questions(client: TestClient, db: Session, llm: FakeLLM) -> None:
    headers = customer_headers(db)
    before = check(client, llm, headers)  # an empty profile: AI use is asked, and the size is assumed
    assert [q["id"] for q in before["questions"]] == ["uses_ai_in_hiring"]
    assert before["workspace_id"] is not None

    save_profile(client, headers, employer_name="Acme Payroll Inc.", headcount=120, uses_ai_in_hiring=False)
    after = check(client, llm, headers)
    assert after["questions"] == []
    assert (result(after, "ON-AI-01")["verdict"], result(after, "ON-AI-01")["message"]) == (
        "pass", "No AI disclosure is needed: you don't use AI to screen, assess or select applicants.",
    )  # fmt: skip
    applies = result(after, "ON-APPL-01")
    assert applies["verdict"] == "pass" and applies["message"].startswith("Your company has 25 or more employees")
    assert after["report"]["versions"]["profile_hash"] != before["report"]["versions"]["profile_hash"]


def test_a_small_headcount_means_the_rules_dont_apply(client: TestClient, db: Session, llm: FakeLLM) -> None:
    headers = customer_headers(db)
    save_profile(client, headers, headcount=12)
    assert result(check(client, llm, headers), "ON-APPL-01")["verdict"] == "not_applicable"


def test_the_profile_headcount_skips_the_web_search(client: TestClient, db: Session, llm: FakeLLM) -> None:
    headers = customer_headers(db)
    employer = f"Acme {secrets.token_hex(3)}"
    save_profile(client, headers, meets_headcount_threshold=True)
    check(client, llm, headers, employer=employer)  # the posting names its employer, but the profile settles it
    assert llm.calls_for(EmployerSize) == []

    save_profile(client, headers, employer_name="Acme Holdings Ltd.", meets_headcount_threshold=None)
    llm.queue(EmployerSize, SIZE)
    searched = check(client, llm, headers, employer=employer)  # no headcount: search the profile's employer
    [search] = llm.calls_for(EmployerSize)
    assert "<employer>Acme Holdings Ltd.</employer>" in search.user
    assert result(searched, "ON-APPL-01")["message"].startswith("Acme Holdings Ltd.: about 1,000 employees")


def test_the_profile_picks_the_plain_wording(client: TestClient, db: Session, llm: FakeLLM) -> None:
    headers = customer_headers(db)
    save_profile(client, headers, uses_ai_in_hiring=True, wording="plain")
    inspected = check(client, llm, headers)
    assert result(inspected, "ON-AI-01")["verdict"] == "fail" and inspected["questions"] == []
    llm.queue(_Rewrite, {"sentence": "2+ years of payroll experience"})
    llm.queue(Classification, {"canadian_experience": [{"sentence": 4, "label": "ok", "reason": "r"}], "vacancy": [], "ai": []})
    refined = client.post(f"{API}/refine", json={"check_id": inspected["check_id"]}).json()
    [disclosure] = [p for p in refined["refinement"]["patches"] if p["rule"] == "ON-AI-01"]
    assert disclosure["after"].strip() == load_wording("CA-ON").text("ai_disclosure", "plain")


def test_visitors_get_no_profile(client: TestClient) -> None:
    assert client.get(f"{API}/workspaces/current").status_code == 401


def test_a_new_user_gets_an_account_and_a_profile(client: TestClient, db: Session) -> None:
    user, headers = make_user(db)  # no account yet: the first signed-in request makes one
    profile = client.get(f"{API}/workspaces/current", headers=headers)
    assert profile.status_code == 200
    db.refresh(user)
    assert user.customer_id is not None
    assert client.get(f"{API}/workspaces/current", headers=headers).json()["id"] == profile.json()["id"]


def test_editing_the_profile(client: TestClient, db: Session) -> None:
    headers = customer_headers(db)
    first = client.get(f"{API}/workspaces/current", headers=headers).json()
    assert client.get(f"{API}/workspaces/current", headers=headers).json()["id"] == first["id"]  # created once
    assert (first["employer_name"], first["headcount"], first["wording"], first["headcount_threshold"]) == (
        None, None, "formal", 25,
    )  # fmt: skip

    saved = save_profile(client, headers, employer_name="  Acme   Payroll ", headcount=40)
    assert (saved["employer_name"], saved["headcount"], saved["meets_headcount_threshold"]) == ("Acme Payroll", 40, None)
    saved = save_profile(client, headers, meets_headcount_threshold=True)  # "25 or more" replaces the number
    assert (saved["employer_name"], saved["headcount"], saved["meets_headcount_threshold"]) == ("Acme Payroll", None, True)
    saved = save_profile(client, headers, uses_ai_in_hiring=True)  # one answer saved during a check
    assert (saved["meets_headcount_threshold"], saved["uses_ai_in_hiring"]) == (True, True)

    url = f"{API}/workspaces/{first['id']}"
    assert client.patch(url, json={"wording": "casual"}, headers=headers).status_code == 422
    assert client.patch(url, json={"headcount": -1}, headers=headers).status_code == 422
    assert client.patch(url, json={"posting": "text"}, headers=headers).status_code == 422  # company facts only
    other = customer_headers(db)
    assert client.patch(url, json={"headcount": 1}, headers=other).status_code == 404


def test_deleting_the_last_account_deletes_the_profile(client: TestClient, db: Session) -> None:
    customer = make_customer(db)
    customer_id = customer.id
    _, first = make_user(db, customer)
    _, second = make_user(db, customer)
    save_profile(client, first, employer_name="Acme Payroll")
    mine = select(Workspace).where(Workspace.customer_id == customer.id)
    assert client.delete(f"{API}/users/me", headers=first).status_code == 200
    assert len(db.exec(mine).all()) == 1  # the other user still checks with it
    assert client.delete(f"{API}/users/me", headers=second).status_code == 200
    assert db.exec(mine).all() == []
    db.expunge(customer)
    assert db.get(Customer, customer_id) is None  # the account and its history go with the last user


# Client workspaces


def create(client: TestClient, headers: dict[str, str], name: str) -> dict[str, Any]:
    response = client.post(f"{API}/workspaces/", json={"name": name}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def patch(client: TestClient, headers: dict[str, str], workspace: dict[str, Any], **fields: Any) -> Any:
    return client.patch(f"{API}/workspaces/{workspace['id']}", json=fields, headers=headers)


def history(client: TestClient, headers: dict[str, str], workspace: dict[str, Any] | None = None) -> list[Any]:
    params = {"workspace_id": workspace["id"]} if workspace else {}
    return client.get(f"{API}/account/checks", params=params, headers=headers).json()["data"]


def test_each_client_workspace_has_its_own_profile_and_history(client: TestClient, db: Session, llm: FakeLLM) -> None:
    headers = customer_headers(db)
    acme, beta = create(client, headers, "Acme Retail"), create(client, headers, "  Beta   Foods ")
    assert (acme["name"], beta["name"], beta["employer_name"], beta["updated_at"]) == ("Acme Retail", "Beta Foods", None, None)
    patch(client, headers, acme, headcount=300, uses_ai_in_hiring=False)
    patch(client, headers, beta, meets_headcount_threshold=True, uses_ai_in_hiring=True, wording="plain")

    for_acme = check(client, llm, headers, workspace=acme["id"])
    for_beta = check(client, llm, headers, workspace=beta["id"])
    assert (for_acme["workspace_id"], for_beta["workspace_id"]) == (acme["id"], beta["id"])
    assert (result(for_acme, "ON-AI-01")["verdict"], result(for_beta, "ON-AI-01")["verdict"]) == ("pass", "fail")
    assert for_acme["questions"] == for_beta["questions"] == []
    check(client, llm, headers)  # no workspace sent: the newest one, which the user last created

    assert [c["workspace_name"] for c in history(client, headers, acme)] == ["Acme Retail"]
    assert [c["workspace_name"] for c in history(client, headers, beta)] == ["Beta Foods", "Beta Foods"]
    assert len(history(client, headers)) == 3
    account = client.get(f"{API}/account", headers=headers).json()
    assert (account["checks_used"], account["checks_limit"]) == (3, None)  # one account, shared by every workspace


def test_switching_renaming_and_archiving(client: TestClient, db: Session, llm: FakeLLM) -> None:
    headers = customer_headers(db)
    first = client.get(f"{API}/workspaces/current", headers=headers).json()  # the empty one every customer gets
    second = create(client, headers, "Beta Foods")
    listed = client.get(f"{API}/workspaces/", headers=headers).json()
    assert ([w["id"] for w in listed["data"]], listed["current_id"], listed["can_create"]) == (
        [first["id"], second["id"]], second["id"], True,
    )  # fmt: skip

    switched = client.put(f"{API}/workspaces/current", json={"workspace_id": first["id"]}, headers=headers)
    assert switched.json()["id"] == first["id"]
    assert client.get(f"{API}/workspaces/current", headers=headers).json()["id"] == first["id"]
    assert check(client, llm, headers)["workspace_id"] == first["id"]  # the one picked, on any device

    assert patch(client, headers, second, name="Beta Foods Inc.").json()["name"] == "Beta Foods Inc."
    assert patch(client, headers, second, name="  ").status_code == 422
    check(client, llm, headers, workspace=second["id"])

    archived = client.post(f"{API}/workspaces/{second['id']}/archive", headers=headers)
    assert [w["id"] for w in archived.json()["data"]] == [first["id"]]
    assert history(client, headers, second)[0]["workspace_name"] == "Beta Foods Inc."  # past checks keep the name
    refused = check(client, llm, headers, workspace=second["id"], status=409)  # a switcher that hasn't refreshed
    assert "archived" in refused["detail"]
    assert client.put(f"{API}/workspaces/current", json={"workspace_id": second["id"]}, headers=headers).status_code == 404
    assert patch(client, headers, second, headcount=5).status_code == 404
    assert client.post(f"{API}/workspaces/{first['id']}/archive", headers=headers).status_code == 409  # the last one


def test_workspaces_belong_to_one_customer(client: TestClient, db: Session, llm: FakeLLM) -> None:
    mine, theirs = customer_headers(db), customer_headers(db)
    other = create(client, theirs, "Their client")
    assert check(client, llm, mine, workspace=other["id"], status=409)  # never another customer's profile
    assert patch(client, mine, other, uses_ai_in_hiring=True).status_code == 404
    assert client.put(f"{API}/workspaces/current", json={"workspace_id": other["id"]}, headers=mine).status_code == 404
    assert client.post(f"{API}/workspaces/{other['id']}/archive", headers=mine).status_code == 404
    assert history(client, mine, other) == []


@pytest.fixture(autouse=True, scope="module")
def clean_up(db: Session) -> Generator[None]:
    yield
    db.execute(delete(PaidCheck))
    for user in db.exec(select(User).where(col(User.customer_id).is_not(None))).all():
        db.delete(user)
    for user in db.exec(select(User).where(col(User.email).like("%@agency.example"))).all():
        db.delete(user)
    db.commit()
    db.execute(delete(Workspace))
    db.execute(delete(Customer))
    db.commit()
