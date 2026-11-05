"""Pay range suggestions through the API, against Postgres, with a scripted LLM (no network): signed-in checks
only, the cost counted, nothing written into a posting until the user confirms, and the confirmed range saved as the
job title's band in the check's workspace. Run `docker compose up -d db` and migrate first.
"""

import uuid
from collections.abc import Generator
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api.free_check import rate_limited
from app.api.routes.checks import get_limits, get_llm, get_posting_date, get_sizes, get_usage
from app.api.routes.pay import get_job_bank, get_postings_cache
from app.compliance.classification import Classification
from app.compliance.extraction import Extraction
from app.compliance.llm import Cited, ModelSettings, SpendMeter
from app.core.config import settings
from app.main import app
from app.models import PayBand, Workspace
from app.pay.suggest import OccupationMatch
from tests.utils.accounts import make_customer, make_user
from tests.compliance.fake_llm import FakeLLM
from tests.compliance.test_api import MemoryLimits, MemoryUsage
from tests.compliance.test_employer import MemorySizes
from tests.compliance.test_inspector import POSTING, extraction, labels
from tests.pay.fixtures import write_job_bank
from tests.pay.test_suggest import MemoryPostings

API = settings.API_V1_STR
NO_PAY = POSTING.replace("Salary: $60,000 – $80,000 per year, plus a $5,000 signing bonus.", "Great benefits.")
NOC = {"code": "13102", "confidence": "high", "alternative": "13100"}
SEARCH = {
    "quotes": [{"text": "$25.00 - $27.00 per hour", "url": "https://www.randstad.ca/jobs/payroll-specialist_1/",
                "title": "Payroll Specialist", "cited_text": "Payroll Specialist - Mississauga - $25.00 - $27.00 per hour"}],
    "results": [{"url": "https://www.randstad.ca/jobs/payroll-specialist_1/", "title": "t", "page_age": "12 days ago"}],
}  # fmt: skip


class PricedLLM(FakeLLM):
    """Each scripted call costs what a real one would, roughly: a search $0.03, a mapping $0.001."""

    def __init__(self) -> None:
        super().__init__()
        self.meter = SpendMeter()

    def fresh(self) -> "PricedLLM":
        """As get_llm gives each request a new wrapper, each request's meter starts at zero."""
        self.meter = SpendMeter()
        return self

    def parse(self, **kwargs: Any) -> Any:
        self.meter.usd += Decimal("0.001")
        return super().parse(**kwargs)

    def cite(self, *, system: str, user: str, settings: ModelSettings, tools: list[dict[str, Any]]) -> Cited:
        self.meter.usd += Decimal("0.03") - Decimal("0.001")  # parse adds the rest
        return super().cite(system=system, user=user, settings=settings, tools=tools)


@pytest.fixture
def env(tmp_path: Path) -> Generator[dict[str, Any]]:
    fake, limits, usage = PricedLLM(), MemoryLimits(per_week=100), MemoryUsage()
    postings, bank = MemoryPostings(), write_job_bank(tmp_path / "data")
    app.dependency_overrides[get_llm] = fake.fresh
    app.dependency_overrides[get_posting_date] = lambda: date(2026, 10, 22)
    app.dependency_overrides[get_limits] = lambda: limits
    app.dependency_overrides[get_usage] = lambda: usage
    app.dependency_overrides[get_sizes] = MemorySizes
    app.dependency_overrides[get_postings_cache] = lambda: postings
    app.dependency_overrides[get_job_bank] = lambda: bank
    app.dependency_overrides[rate_limited] = lambda: None
    yield {"llm": fake, "limits": limits, "usage": usage}
    for dependency in (get_llm, get_posting_date, get_limits, get_usage, get_sizes, get_postings_cache, get_job_bank,
                       rate_limited):  # fmt: skip
        app.dependency_overrides.pop(dependency, None)


def checked(client: TestClient, llm: FakeLLM, headers: dict[str, str] | None = None, **body: Any) -> dict[str, Any]:
    """A check of a posting without pay, refined: the fixes hold the pay placeholder."""
    llm.queue(Extraction, extraction(pay=[])).queue(Classification, labels(canadian_experience=[
        {"sentence": i, "label": "ok", "reason": "r"} for i in (1, 4, 5, 6)
    ]))  # fmt: skip
    inspected = client.post(f"{API}/inspect", json={"text": NO_PAY, **body}, headers=headers or {})
    assert inspected.status_code == 200, inspected.text
    refined = client.post(f"{API}/refine", json={"check_id": inspected.json()["check_id"]})
    assert refined.status_code == 200, refined.text
    return refined.json()


def pay_patch(check: dict[str, Any]) -> dict[str, Any]:
    return next(p for p in check["refinement"]["patches"] if p["rule"] == "ON-PAY-01")


def suggest(client: TestClient, headers: dict[str, str], check_id: str, **body: Any) -> Any:
    return client.post(f"{API}/pay/suggest", json={"check_id": check_id, **body}, headers=headers)


def confirm(client: TestClient, headers: dict[str, str], check_id: str, low: str, high: str, unit: str = "hour") -> Any:
    return client.post(
        f"{API}/pay/confirm", json={"check_id": check_id, "min": low, "max": high, "unit": unit}, headers=headers
    )


def test_suggest_then_confirm(client: TestClient, db: Session, env: dict[str, Any]) -> None:
    llm, usage, limits = env["llm"], env["usage"], env["limits"]
    _, headers = make_user(db, make_customer(db))
    check = checked(client, llm, headers)
    assert pay_patch(check)["after"].strip() == "[Pay range: add before publishing]"

    llm.queue(OccupationMatch, NOC).queue(Cited, SEARCH)
    response = suggest(client, headers, check["check_id"])
    assert response.status_code == 200, response.text
    found = response.json()
    assert (found["status"], found["occupation"]["code"], found["region"]) == ("suggested", "13102", "Toronto")
    assert found["suggested"] == {"min": "23.00", "max": "39.50", "unit": "hour"}
    assert [s["kind"] for s in found["sources"]] == ["job_bank", "posting"]
    assert found["sources"][1]["figures"] == "$25–$27 an hour" and found["sources"][1]["date"] == "Posted 12 days ago"

    # The cost is counted, once, in the usage events and the day's spend meter.
    [event] = [e for e in usage.events if e["kind"] == "pay_suggest"]
    assert (event["usd"], event["status"], event["plan"], event["check_id"]) == (
        Decimal("0.031"), "suggested", "account", check["check_id"],
    )  # fmt: skip
    assert limits.spent == Decimal("0.031")
    assert suggest(client, headers, check["check_id"]).json() == found  # asked again: no new model calls
    assert len(llm.calls_for(OccupationMatch)) == 1 and limits.spent == Decimal("0.031")

    # A suggestion changes nothing: the posting keeps the placeholder until the customer confirms.
    refined = client.post(f"{API}/refine", json={"check_id": check["check_id"]}).json()
    assert pay_patch(refined)["after"].strip() == "[Pay range: add before publishing]"

    response = confirm(client, headers, check["check_id"], "28.00", "32.50")
    assert response.status_code == 200, response.text
    patch = pay_patch(response.json())
    assert (patch["after"], patch["confirmed"], patch["default"]) == ("\nExpected pay: $28-$32.50 an hour", True, True)
    final = client.post(f"{API}/patches/accept", json={"check_id": check["check_id"], "decisions": []}).json()
    assert "Great benefits.\nExpected pay: $28-$32.50 an hour\n" in final["text"]
    assert next(r for r in final["report"]["results"] if r["rule"] == "ON-PAY-01")["verdict"] == "pass"
    assert [e["kind"] for e in usage.events].count("pay_confirm") == 1

    band = db.exec(select(PayBand).where(PayBand.workspace_id == uuid.UUID(check["workspace_id"]))).one()
    assert (band.role, band.title, band.min, band.max, band.unit) == (
        "payroll specialist", "Payroll Specialist", Decimal("28.00"), Decimal("32.50"), "hour",
    )  # fmt: skip

    # The next posting for the same job starts from the confirmed band.
    again = checked(client, llm, headers)
    llm.queue(OccupationMatch, NOC)  # the postings search is cached for a week
    found = suggest(client, headers, again["check_id"]).json()
    assert found["sources"][0]["kind"] == "band" and found["band"] == {"min": "28.00", "max": "32.50", "unit": "hour"}
    assert found["suggested"] == found["band"] and found["flag"] is None


def test_signed_in_checks_only(client: TestClient, db: Session, env: dict[str, Any]) -> None:
    llm = env["llm"]
    _, paid = make_user(db, make_customer(db))
    free = checked(client, llm)  # a visitor's free check keeps the placeholder
    assert pay_patch(free)["after"].strip() == "[Pay range: add before publishing]"

    assert suggest(client, {}, free["check_id"]).status_code == 401
    refused = suggest(client, paid, free["check_id"])  # an account can't use a visitor's free check
    assert refused.status_code == 403 and refused.json()["detail"] == "Pay range suggestions are for checks you ran signed in."

    mine = checked(client, llm, paid)
    _, other = make_user(db, make_customer(db))
    assert suggest(client, other, mine["check_id"]).status_code == 403  # another customer's check
    assert confirm(client, other, mine["check_id"], "28", "32").status_code == 403
    assert suggest(client, paid, "expired").status_code == 404
    assert llm.calls_for(OccupationMatch) == [] and llm.calls_for(Cited) == []


def test_low_confidence_asks_for_the_occupation_first(client: TestClient, db: Session, env: dict[str, Any]) -> None:
    llm = env["llm"]
    _, headers = make_user(db, make_customer(db))
    check = checked(client, llm, headers)
    llm.queue(OccupationMatch, {**NOC, "confidence": "low"})
    pick = suggest(client, headers, check["check_id"]).json()
    assert pick["status"] == "pick_occupation" and [o["code"] for o in pick["alternatives"]] == ["13102", "13100"]
    assert llm.calls_for(Cited) == []

    llm.queue(Cited, SEARCH)
    picked = suggest(client, headers, check["check_id"], noc_code="13100").json()
    assert (picked["status"], picked["occupation"]["code"]) == ("suggested", "13100")
    assert suggest(client, headers, check["check_id"], noc_code="1310").status_code == 422


def test_confirm_keeps_the_range_within_the_cap(client: TestClient, db: Session, env: dict[str, Any]) -> None:
    llm = env["llm"]
    _, headers = make_user(db, make_customer(db))
    check = checked(client, llm, headers)
    too_wide = confirm(client, headers, check["check_id"], "60000", "115000", "year")
    assert too_wide.status_code == 422
    assert too_wide.json()["detail"] == "That range is $55,000 a year wide. Keep it within $50,000 a year."
    assert confirm(client, headers, check["check_id"], "32", "28").status_code == 422
    assert db.exec(select(PayBand).where(PayBand.workspace_id == uuid.UUID(check["workspace_id"]))).first() is None
    assert confirm(client, headers, check["check_id"], "60000", "110000", "year").status_code == 200  # exactly $50,000


def test_an_agency_band_belongs_to_the_checks_client(client: TestClient, db: Session, env: dict[str, Any]) -> None:
    llm = env["llm"]
    _, headers = make_user(db, make_customer(db))
    first = client.get(f"{API}/workspaces/current", headers=headers).json()
    second = client.post(f"{API}/workspaces/", json={"name": "Maple Grocers"}, headers=headers).json()
    check = checked(client, llm, headers, workspace_id=second["id"])
    assert check["workspace_id"] == second["id"]
    assert confirm(client, headers, check["check_id"], "70000", "80000", "year").status_code == 200

    bands = client.get(f"{API}/pay/bands", params={"workspace_id": second["id"]}, headers=headers).json()["data"]
    assert [(b["title"], b["min"], b["max"], b["unit"]) for b in bands] == [("Payroll Specialist", "70000.00", "80000.00", "year")]
    assert client.get(f"{API}/pay/bands", params={"workspace_id": first["id"]}, headers=headers).json()["data"] == []

    _, stranger = make_user(db, make_customer(db))
    assert client.delete(f"{API}/pay/bands/{bands[0]['id']}", headers=stranger).status_code == 404
    assert client.delete(f"{API}/pay/bands/{bands[0]['id']}", headers=headers).status_code == 200
    assert db.get(Workspace, uuid.UUID(second["id"])) is not None
    db.expire_all()
    assert db.exec(select(PayBand).where(PayBand.workspace_id == uuid.UUID(second["id"]))).first() is None
