"""Outreach reports against Postgres: saved by the outreach workflow with its key, opened by link, answered, saved
to an account, listed for us, and deleted when nobody saves them. Run `docker compose up -d db` and migrate first.
"""

import json
from collections.abc import Generator
from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, delete, select

from app.api.billing import free_customer
from app.compliance.classification import Classification
from app.compliance.extraction import Extraction
from app.compliance.rulepack import load_pack
from app.core.config import settings
from app.models import Customer, OutreachPosting, OutreachReport, User, get_datetime_utc
from app.outreach_report import report_body, save_report
from app.prospect import MemorySizes, prospect, save_texts
from tests.api.routes.test_audits import CAREERS, northwind
from tests.api.routes.test_billing import make_user
from tests.compliance.fake_llm import FakeLLM
from tests.compliance.test_inspector import extraction, labels

API = settings.API_V1_STR
KEY = "outreach-test-key"
AUTH = {"Authorization": f"Bearer {KEY}"}


@pytest.fixture(autouse=True)
def outreach_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "OUTREACH_API_KEY", KEY)


def report_in(**changes: Any) -> dict[str, Any]:
    finding = {
        "rule": "ON-VAC-01", "verdict": "fail", "message": "The posting doesn't say whether it is for an existing vacancy.",
        "quotes": [],
    }  # fmt: skip
    form = {"rule": "ON-CEX-01", "verdict": "fail", "message": "A required question asks for Canadian experience.",
            "quotes": ["Do you have Canadian work experience?"]}  # fmt: skip
    return {
        "company": "Acme", "url": "https://jobs.lever.co/acme", "found": 4, "outside_ontario": 1,
        "postings": [
            {"title": "Payroll Specialist", "location": "Toronto, ON", "url": "https://jobs.lever.co/acme/1",
             "where": "ontario", "status": "not_compliant", "findings": [finding], "form_status": "not_compliant",
             "form_findings": [form]},
            {"title": "Accountant", "location": "Ottawa, ON", "url": "https://jobs.lever.co/acme/2", "where": "ontario",
             "status": "compliant", "form_status": "compliant"},
            {"title": "Analyst", "url": "https://jobs.lever.co/acme/3", "where": "canada", "status": "failed",
             "note": "The posting's page didn't open."},
        ],
        **changes,
    }  # fmt: skip


def create(client: TestClient, **changes: Any) -> dict[str, Any]:
    response = client.post(f"{API}/outreach/reports", json=report_in(**changes), headers=AUTH)
    assert response.status_code == 200, response.text
    return response.json()


def free_user(db: Session) -> tuple[User, dict[str, str]]:
    customer = free_customer("hr@acme.example", get_datetime_utc())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return make_user(db, customer)


def test_saving_a_report_takes_the_outreach_key(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    assert client.post(f"{API}/outreach/reports", json=report_in()).status_code == 401
    wrong = client.post(f"{API}/outreach/reports", json=report_in(), headers={"Authorization": "Bearer nope"})
    assert wrong.status_code == 401
    monkeypatch.setattr(settings, "OUTREACH_API_KEY", None)
    assert client.post(f"{API}/outreach/reports", json=report_in(), headers=AUTH).status_code == 503


def test_a_report_is_refused_with_an_unknown_rule_or_a_bad_link(client: TestClient) -> None:
    bad = report_in()
    bad["postings"][0]["findings"][0]["rule"] = "ON-XYZ-01"
    assert client.post(f"{API}/outreach/reports", json=bad, headers=AUTH).status_code == 422
    assert client.post(f"{API}/outreach/reports", json=report_in(url="javascript:alert(1)"), headers=AUTH).status_code == 422


def test_the_link_opens_the_report_without_signing_in(client: TestClient, db: Session) -> None:
    created = create(client)
    assert created["link"] == f"{settings.FRONTEND_HOST}/report/{created['token']}"
    report = client.get(f"{API}/reports/{created['token']}").json()
    assert (report["company"], report["found"], report["outside_ontario"]) == ("Acme", 4, 1)
    assert [p["title"] for p in report["postings"]] == ["Payroll Specialist", "Accountant", "Analyst"]
    first = report["postings"][0]
    assert first["findings"][0]["rule"] == "ON-VAC-01" and first["form_findings"][0]["quotes"] == [
        "Do you have Canadian work experience?"
    ]
    assert not report["saved"] and not report["mine"] and report["expires_on"] is not None
    assert client.get(f"{API}/reports/not-a-token").status_code == 404

    row = db.exec(select(OutreachReport).where(OutreachReport.token == created["token"])).one()
    assert row.views == 1 and row.first_viewed_at is not None


def test_our_own_views_are_not_counted(client: TestClient, db: Session, superuser_token_headers: dict[str, str]) -> None:
    created = create(client)
    client.get(f"{API}/reports/{created['token']}", headers=superuser_token_headers)
    row = db.exec(select(OutreachReport).where(OutreachReport.token == created["token"])).one()
    assert row.views == 0 and row.first_viewed_at is None


def test_the_hiring_process_questions_are_answered_on_the_report(client: TestClient) -> None:
    token = create(client)["token"]
    answered = client.put(f"{API}/reports/{token}/checklist", json={"answers": {"ON-INT-01": "yes"}})
    assert answered.status_code == 200 and answered.json()["checklist"] == {"ON-INT-01": "yes"}
    both = client.put(f"{API}/reports/{token}/checklist", json={"answers": {"ON-REC-01": "unsure"}}).json()
    assert both["checklist"] == {"ON-INT-01": "yes", "ON-REC-01": "unsure"}
    assert client.put(f"{API}/reports/{token}/checklist", json={"answers": {"ON-PAY-01": "yes"}}).status_code == 422
    assert client.put(f"{API}/reports/{token}/checklist", json={"answers": {"ON-INT-01": "maybe"}}).status_code == 422


def test_a_report_is_saved_to_one_account(client: TestClient, db: Session) -> None:
    token = create(client)["token"]
    assert client.post(f"{API}/reports/{token}/save").status_code == 401
    _, no_account = make_user(db)
    assert client.post(f"{API}/reports/{token}/save", headers=no_account).status_code == 409

    user, headers = free_user(db)
    saved = client.post(f"{API}/reports/{token}/save", headers=headers)
    assert saved.status_code == 200 and saved.json()["saved"] and saved.json()["mine"]
    assert saved.json()["expires_on"] is None
    assert client.post(f"{API}/reports/{token}/save", headers=headers).status_code == 200  # again: no change
    [mine] = client.get(f"{API}/reports", headers=headers).json()
    assert (mine["token"], mine["postings"], mine["to_fix"]) == (token, 3, 1)

    _, other = free_user(db)
    assert client.post(f"{API}/reports/{token}/save", headers=other).status_code == 409
    assert client.get(f"{API}/reports", headers=other).json() == []
    assert client.get(f"{API}/reports/{token}", headers=other).json()["mine"] is False


def test_we_see_every_report_with_its_views_and_who_saved_it(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    token = create(client)["token"]
    client.get(f"{API}/reports/{token}")
    user, headers = free_user(db)
    client.post(f"{API}/reports/{token}/save", headers=headers)
    rows = client.get(f"{API}/outreach/reports", headers=superuser_token_headers).json()
    row = next(r for r in rows if r["token"] == token)
    assert (row["company"], row["views"], row["saved_by"]) == ("Acme", 1, "hr@acme.example")
    _, normal = make_user(db)
    assert client.get(f"{API}/outreach/reports", headers=normal).status_code == 403


def test_a_posting_that_only_asks_a_question_is_not_counted_to_fix(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    def finding(rule: str, verdict: str) -> dict[str, Any]:
        return {"rule": rule, "verdict": verdict, "message": "A message.", "quotes": []}

    def posting(n: int, findings: list[dict[str, Any]], form_status: str | None = None) -> dict[str, Any]:
        return {
            "title": f"Posting {n}", "url": f"https://jobs.lever.co/acme/{n}", "where": "ontario",
            "status": "needs_input", "findings": findings, "form_status": form_status,
        }  # fmt: skip

    question = finding("ON-AI-01", "needs_input")
    token = create(client, postings=[
        posting(1, [question]),  # only a question: not counted
        posting(2, [question], "compliant"),  # and its form is fine: not counted
        posting(3, [finding("ON-PAY-01", "fail"), question]),
        posting(4, [finding("ON-VAC-01", "warning")]),
        posting(5, [question], "not_compliant"),
        {**posting(6, [], "compliant"), "form_findings": [finding("ON-CEX-01", "warning")]},
    ])["token"]  # fmt: skip

    report = client.get(f"{API}/reports/{token}").json()
    assert [p["title"] for p in report["postings"][:2]] == ["Posting 1", "Posting 2"]  # still on the report

    _, headers = free_user(db)
    client.post(f"{API}/reports/{token}/save", headers=headers)
    [mine] = client.get(f"{API}/reports", headers=headers).json()
    assert (mine["postings"], mine["to_fix"]) == (6, 4)
    rows = client.get(f"{API}/outreach/reports", headers=superuser_token_headers).json()
    assert next(r for r in rows if r["token"] == token)["to_fix"] == 4


def test_a_report_nobody_saved_is_deleted_after_its_days(client: TestClient, db: Session) -> None:
    old, kept = create(client)["token"], create(client)["token"]
    _, headers = free_user(db)
    client.post(f"{API}/reports/{kept}/save", headers=headers)
    long_ago = get_datetime_utc() - timedelta(days=settings.REPORT_DAYS + 1)
    for token in (old, kept):
        row = db.exec(select(OutreachReport).where(OutreachReport.token == token)).one()
        row.created_at = long_ago
        db.add(row)
    db.commit()
    assert client.get(f"{API}/reports/{old}").status_code == 404  # expired, before any purge
    create(client)  # a new report purges the old ones
    db.expire_all()
    assert db.exec(select(OutreachReport).where(OutreachReport.token == old)).first() is None
    assert client.get(f"{API}/reports/{kept}").status_code == 200  # saved: kept


def test_the_outreach_command_saves_a_checked_board_as_a_report(client: TestClient, tmp_path: Any) -> None:
    llm = FakeLLM()
    for _ in range(4):
        llm.queue(Extraction, extraction()).queue(Classification, labels())
    checked = prospect(CAREERS, northwind().fetcher(), llm, load_pack("CA-ON"), date(2026, 10, 23), MemorySizes())
    check = save_texts(checked, tmp_path / "northwind")  # as the workflow keeps it: texts in files, not the JSON
    body = report_body(check, "Northwind")
    assert "text_file" not in json.dumps(body)  # only what the report shows leaves this machine
    saved = save_report(body, "http://testserver", KEY, client)
    report = client.get(f"{API}/reports/{saved['token']}").json()
    assert (report["company"], report["found"], report["outside_ontario"]) == ("Northwind", 4, 1)
    assert len(report["postings"]) == len(check["postings"])
    cex = next(f for f in report["postings"][0]["findings"] if f["rule"] == "ON-CEX-01")
    assert any("Canadian payroll experience" in quote for quote in cex["quotes"])


@pytest.fixture(autouse=True, scope="module")
def clean_up(db: Session) -> Generator[None]:
    yield
    db.execute(delete(OutreachPosting))
    db.execute(delete(OutreachReport))
    for user in db.exec(select(User).where(col(User.customer_id).is_not(None))).all():
        db.delete(user)
    db.execute(delete(Customer))
    db.commit()
