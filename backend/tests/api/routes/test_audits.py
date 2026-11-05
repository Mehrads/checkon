"""Careers page audits through the API, against Postgres, with a recorded web and a scripted LLM (no network):
signed-in accounts only, the postings and checks shown before anything runs, one check per posting counted for the
account,
the report kept without the posting text, and the full check open for an hour. Run `docker compose up -d db` and
migrate first.
"""

import json
from collections.abc import Generator
from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, delete, select

from app.api.check_store import CheckStore
from app.api.free_check import rate_limited
from app.api.routes.audits import AuditMemory, get_fetcher, get_memory
from app.api.routes.checks import (
    get_limits,
    get_llm,
    get_posting_date,
    get_sizes,
    get_store,
    get_usage,
)
from app.audit.boards import read_board
from app.compliance.classification import Classification
from app.compliance.extraction import Extraction
from app.compliance.refiner import _Rewrite
from app.core.config import settings
from app.main import app
from app.models import (
    Audit,
    AuditPosting,
    Customer,
    PaidCheck,
    User,
    Workspace,
    get_datetime_utc,
)
from tests.audit.web import Web, boards
from tests.compliance.fake_llm import FakeLLM
from tests.compliance.test_api import MemoryLimits, MemoryUsage
from tests.compliance.test_employer import MemorySizes
from tests.compliance.test_inspector import POSTING, extraction, labels
from tests.utils.accounts import make_customer, make_user

API = settings.API_V1_STR
CAREERS = "https://northwind.example/careers"
# The sample posting as a careers page's job data: the page's text is exactly the pasted sample's
DESCRIPTION = (
    "<p>About the role<br>We're growing. You'll run payroll for 400 employees.</p><p>Requirements:<br>"
    "• 2+ years of Canadian payroll experience<br>• CPP certification is an asset<br>• Excellent communication skills"
    "</p><p>Compensation<br>Salary: $60,000 – $80,000 per year, plus a $5,000 signing bonus.</p>"
    "<p>This posting is for an existing vacancy.</p>"
)  # fmt: skip


def job_page(title: str, location: str) -> str:
    data = {"@context": "https://schema.org", "@type": "JobPosting", "title": title, "description": DESCRIPTION,
            "jobLocation": {"@type": "Place", "address": location}}  # fmt: skip
    return f'<html><head><script type="application/ld+json">{json.dumps(data)}</script></head><body></body></html>'


def northwind() -> Web:
    web = boards()
    web.page("northwind.example/careers", "".join(
        f'<a href="/jobs/{slug}">{slug}</a>' for slug in ("payroll-mississauga", "payroll-brampton", "payroll-canada",
                                                          "payroll-calgary")
    ))  # fmt: skip
    web.page("northwind.example/jobs/payroll-mississauga", job_page("Payroll Specialist", "Mississauga, ON (hybrid)"))
    web.page("northwind.example/jobs/payroll-brampton", job_page("Payroll Specialist", "Mississauga, ON (hybrid)"))
    web.page("northwind.example/jobs/payroll-canada", job_page("Payroll Lead", "Remote, Canada"))
    web.page("northwind.example/jobs/payroll-calgary", job_page("Payroll Clerk", "Calgary, AB"))
    return web


@pytest.fixture
def env() -> Generator[dict[str, Any]]:
    fake, web, store, memory = FakeLLM(), northwind(), CheckStore(), AuditMemory()
    app.dependency_overrides[get_llm] = lambda: fake
    app.dependency_overrides[get_posting_date] = lambda: date(2026, 10, 22)
    app.dependency_overrides[get_limits] = lambda: MemoryLimits(per_week=0, budget=0)  # free checks all refused
    app.dependency_overrides[get_usage] = MemoryUsage
    app.dependency_overrides[get_sizes] = MemorySizes
    app.dependency_overrides[rate_limited] = lambda: None
    app.dependency_overrides[get_fetcher] = lambda: web.fetcher()
    app.dependency_overrides[get_store] = lambda: env_state["store"]
    app.dependency_overrides[get_memory] = lambda: env_state["memory"]
    env_state = {"llm": fake, "web": web, "store": store, "memory": memory}
    yield env_state
    for dependency in (get_llm, get_posting_date, get_limits, get_usage, get_sizes, rate_limited, get_fetcher,
                       get_store, get_memory):  # fmt: skip
        app.dependency_overrides.pop(dependency, None)


def headers_for(db: Session) -> dict[str, str]:
    return make_user(db, make_customer(db))[1]


def preview(client: TestClient, headers: dict[str, str], url: str = CAREERS, **body: Any) -> Any:
    return client.post(f"{API}/audits/preview", json={"url": url, **body}, headers=headers)


def start(client: TestClient, headers: dict[str, str], found: dict[str, Any], ids: list[str] | None = None) -> Any:
    ids = ids if ids is not None else [p["id"] for p in found["postings"] if p["where"] == "ontario"]
    return client.post(f"{API}/audits/", json={"preview_id": found["preview_id"], "posting_ids": ids}, headers=headers)


def check(client: TestClient, env: dict[str, Any], headers: dict[str, str], audit: dict[str, Any], n: int,
          **answers: Any) -> Any:  # fmt: skip
    llm: FakeLLM = env["llm"]
    if answers.get("queue", True):
        llm.queue(Extraction, extraction(**answers.get("extraction", {}))).queue(Classification, labels())
    posting = audit["postings"][n]
    return client.post(f"{API}/audits/{audit['id']}/postings/{posting['id']}/check", headers=headers)


def paid_checks(client: TestClient, headers: dict[str, str]) -> list[dict[str, Any]]:
    return client.get(f"{API}/account/checks", headers=headers).json()["data"]


def test_the_careers_page_reads_as_the_pasted_posting() -> None:
    board = read_board(CAREERS, northwind().fetcher(), date(2026, 10, 22))
    assert board.postings[0].text == POSTING.strip()


def test_audits_need_a_signed_in_user(client: TestClient, env: dict[str, Any]) -> None:
    assert preview(client, {}).status_code == 401
    assert env["web"].requests == []


def test_preview_then_check_each_posting(client: TestClient, db: Session, env: dict[str, Any]) -> None:
    headers = headers_for(db)
    response = preview(client, headers, url="northwind.example/careers")  # https:// added
    assert response.status_code == 200, response.text
    found = response.json()
    assert [(p["title"], p["where"]) for p in found["postings"]] == [
        ("Payroll Specialist", "ontario"), ("Payroll Specialist", "ontario"), ("Payroll Lead", "canada"),
    ]  # Ontario first; Calgary left out
    assert (found["source"], found["outside_ontario"], found["more"], found["max_postings"]) == ("page", 1, 0, 50)
    assert (found["checks_left"], found["workspace_name"]) == (None, "Your company")  # no limit by default
    assert env["llm"].calls == [] and paid_checks(client, headers) == []  # nothing checked or charged yet

    response = start(client, headers, found)
    assert response.status_code == 201, response.text
    audit = response.json()
    assert [p["status"] for p in audit["postings"]] == ["queued", "queued"]
    assert start(client, headers, found).status_code == 404  # a preview starts one audit

    first = check(client, env, headers, audit, 0)
    assert first.status_code == 200, first.text
    posting = first.json()
    assert posting["status"] == "not_compliant" and posting["check_open"]
    assert {"rule": "ON-CEX-01", "verdict": "fail"} in posting["issues"]
    assert [issue["verdict"] for issue in posting["issues"]] == sorted(
        (issue["verdict"] for issue in posting["issues"]), key=["fail", "warning", "needs_input"].index
    )
    history = paid_checks(client, headers)
    assert [(c["title"], c["status"]) for c in history] == [("Payroll Specialist", "not_compliant")]

    calls = len(env["llm"].calls)
    again = check(client, env, headers, audit, 0, queue=False)
    assert again.json()["status"] == "not_compliant" and len(env["llm"].calls) == calls  # still open: not redone
    assert len(paid_checks(client, headers)) == 1

    assert check(client, env, headers, audit, 1).json()["status"] == "not_compliant"
    assert client.get(f"{API}/account", headers=headers).json()["checks_used"] == 2

    full = client.get(f"{API}/audits/{audit['id']}/postings/{audit['postings'][0]['id']}", headers=headers)
    assert full.status_code == 200, full.text
    assert full.json()["text"].startswith("Payroll Specialist") and full.json()["report"]["status"] == "not_compliant"
    env["llm"].queue(_Rewrite, {"sentence": "2+ years of payroll experience"})
    env["llm"].queue(Classification, {"canadian_experience": [{"sentence": 4, "label": "ok", "reason": "r"}],
                                      "vacancy": [], "ai": []})  # fmt: skip
    refined = client.post(f"{API}/refine", json={"check_id": full.json()["check_id"]})  # the fixes, as for a paste
    assert refined.status_code == 200, refined.text
    assert any(p["rule"] == "ON-CEX-01" for p in refined.json()["refinement"]["patches"])
    accepted = client.post(f"{API}/patches/accept", json={"check_id": full.json()["check_id"]})
    assert accepted.status_code == 200, accepted.text
    report = client.get(f"{API}/audits/{audit['id']}", headers=headers).json()
    assert report["postings"][0]["final_status"] == accepted.json()["report"]["status"]  # the fixed version's result
    assert report["postings"][0]["status"] == "not_compliant"  # the posting on the board is unchanged

    listed = client.get(f"{API}/audits/", headers=headers).json()
    assert listed["count"] == 1 and listed["data"][0]["statuses"] == {"not_compliant": 2}

    stored = db.exec(select(Audit).where(Audit.id == audit["id"])).one()
    rows = db.exec(select(AuditPosting).where(AuditPosting.audit_id == stored.id)).all()
    kept = json.dumps([stored.model_dump(mode="json"), *(row.model_dump(mode="json") for row in rows)])
    assert "run payroll for 400" not in kept and "Canadian payroll experience" not in kept  # never the posting text


def test_an_expired_check_can_run_again(client: TestClient, db: Session, env: dict[str, Any]) -> None:
    headers = headers_for(db)
    audit = start(client, headers, preview(client, headers).json()).json()
    check(client, env, headers, audit, 0)
    env["store"], env["memory"] = CheckStore(), AuditMemory()  # an hour later: the check and the text are gone

    report = client.get(f"{API}/audits/{audit['id']}", headers=headers).json()
    assert report["postings"][0]["status"] == "not_compliant" and not report["postings"][0]["check_open"]
    expired = client.get(f"{API}/audits/{audit['id']}/postings/{audit['postings'][0]['id']}", headers=headers)
    assert expired.status_code == 410 and expired.json()["detail"]["reason"] == "expired"
    assert expired.headers["cache-control"] == "no-store"  # so the check run again is fetched, not a kept 410

    rerun = check(client, env, headers, audit, 0)  # read from the careers page again
    assert rerun.json()["check_open"] and len(paid_checks(client, headers)) == 2
    assert env["web"].asked().count("northwind.example/jobs/payroll-mississauga") == 2

    env["web"].pages.pop("northwind.example/jobs/payroll-brampton")  # taken down since
    gone = check(client, env, headers, audit, 1, queue=False)
    assert gone.json()["status"] == "failed" and "answered 404" in gone.json()["note"]
    assert len(paid_checks(client, headers)) == 2  # no check used


def test_a_posting_that_cant_be_checked_uses_no_check(client: TestClient, db: Session, env: dict[str, Any]) -> None:
    headers = headers_for(db)
    audit = start(client, headers, preview(client, headers).json()).json()
    french = check(client, env, headers, audit, 0, extraction={"contains_french": True})
    assert french.json()["status"] == "refused" and "French" in french.json()["note"]
    assert paid_checks(client, headers) == []


def test_one_posting_at_a_time(client: TestClient, db: Session, env: dict[str, Any]) -> None:
    headers = headers_for(db)
    audit = start(client, headers, preview(client, headers).json()).json()
    row = db.get(AuditPosting, audit["postings"][0]["id"])
    assert row is not None
    row.status, row.checked_at = "checking", get_datetime_utc()
    db.add(row)
    db.commit()
    assert check(client, env, headers, audit, 0, queue=False).status_code == 409
    row.checked_at = get_datetime_utc() - timedelta(minutes=10)  # it never finished
    db.add(row)
    db.commit()
    assert client.get(f"{API}/audits/{audit['id']}", headers=headers).json()["postings"][0]["status"] == "failed"
    assert check(client, env, headers, audit, 0).json()["status"] == "not_compliant"


@pytest.mark.usefixtures("env")
def test_the_account_limit_bounds_an_audit(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    headers = headers_for(db)
    monkeypatch.setattr(settings, "ACCOUNT_CHECKS_PER_30_DAYS", 2)
    found = preview(client, headers).json()
    assert found["checks_left"] == 2
    ids = [p["id"] for p in found["postings"]]
    too_many = start(client, headers, found, ids)
    assert too_many.status_code == 429 and "2 checks left" in too_many.json()["detail"]["message"]
    assert start(client, headers, found, ["https://example.com/not-on-this-board"]).status_code == 422
    assert start(client, headers, found, ids[:2]).status_code == 201  # the preview is kept after a refusal
    over = client.post(f"{API}/audits/", json={"preview_id": "x", "posting_ids": [str(n) for n in range(51)]},
                       headers=headers)  # fmt: skip
    assert over.status_code == 422  # at most 50 postings in one audit


@pytest.mark.usefixtures("env")
def test_audits_belong_to_their_customer(client: TestClient, db: Session) -> None:
    headers, other = headers_for(db), headers_for(db)
    found = preview(client, headers).json()
    assert start(client, other, found).status_code == 404
    audit = start(client, headers, found).json()
    posting = audit["postings"][0]["id"]
    assert client.get(f"{API}/audits/{audit['id']}", headers=other).status_code == 404
    assert client.post(f"{API}/audits/{audit['id']}/postings/{posting}/check", headers=other).status_code == 404
    assert client.get(f"{API}/audits/{audit['id']}/postings/{posting}", headers=other).status_code == 404
    assert client.get(f"{API}/audits/", headers=other).json()["count"] == 0


def test_an_audit_uses_the_picked_client(client: TestClient, db: Session, env: dict[str, Any]) -> None:
    headers = headers_for(db)
    client.post(f"{API}/workspaces/", json={"name": "Acme Retail"}, headers=headers)
    beta = client.post(f"{API}/workspaces/", json={"name": "Beta Foods"}, headers=headers).json()
    client.patch(f"{API}/workspaces/{beta['id']}", json={"headcount": 40, "uses_ai_in_hiring": True}, headers=headers)
    found = preview(client, headers, workspace_id=beta["id"]).json()
    assert found["workspace_name"] == "Beta Foods"
    audit = start(client, headers, found).json()
    assert audit["workspace_name"] == "Beta Foods"
    posting = check(client, env, headers, audit, 0).json()
    assert {"rule": "ON-AI-01", "verdict": "fail"} in posting["issues"]  # the client uses AI; the posting doesn't say
    assert [c["workspace_name"] for c in paid_checks(client, headers)] == ["Beta Foods"]
    assert client.get(f"{API}/audits/", params={"workspace_id": beta["id"]}, headers=headers).json()["count"] == 1


def test_boards_that_cant_be_read(client: TestClient, db: Session, env: dict[str, Any]) -> None:
    headers = headers_for(db)
    robots = preview(client, headers, url="https://jobs.smartrecruiters.com/NorthwindLogistics")
    assert robots.status_code == 422 and robots.json()["detail"]["reason"] == "robots"
    internal = preview(client, headers, url="http://localhost:8000/admin")
    assert internal.status_code == 422 and internal.json()["detail"]["reason"] == "blocked"
    env["web"].addresses["intranet.example"] = ["10.1.2.3"]
    private = preview(client, headers, url="https://intranet.example/careers")
    assert private.status_code == 422 and private.json()["detail"]["reason"] == "blocked"
    empty = preview(client, headers, url="https://northwind.example/about")
    assert empty.status_code == 422 and empty.json()["detail"]["reason"] == "not_found"


@pytest.mark.usefixtures("env")
def test_deleting_the_last_account_deletes_its_audits(client: TestClient, db: Session) -> None:
    customer = make_customer(db)
    customer_id = customer.id
    _, headers = make_user(db, customer)
    start(client, headers, preview(client, headers).json())
    assert client.delete(f"{API}/users/me", headers=headers).status_code == 200
    assert db.exec(select(Audit).where(Audit.customer_id == customer_id)).all() == []


@pytest.fixture(autouse=True, scope="module")
def clean_up(db: Session) -> Generator[None]:
    yield
    db.execute(delete(Audit))
    db.execute(delete(PaidCheck))
    for user in db.exec(select(User).where(col(User.customer_id).is_not(None))).all():
        db.delete(user)
    for user in db.exec(select(User).where(col(User.email).like("%@agency.example"))).all():
        db.delete(user)
    db.commit()
    db.execute(delete(Workspace))
    db.execute(delete(Customer))
    db.commit()
