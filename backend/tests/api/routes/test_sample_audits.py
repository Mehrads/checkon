"""The free sample audit on the public site, with a recorded web and a scripted LLM (no network): the first postings
only, findings without fixes, a weekly quota used by the first check, and the free checks' daily spend cap."""

from collections.abc import Generator
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.free_check import rate_limited
from app.api.routes.audits import get_fetcher
from app.api.routes.checks import get_llm, get_posting_date, get_sizes, get_usage
from app.api.routes.sample_audits import SampleStore, get_sample_limits, get_samples
from app.compliance.classification import Classification
from app.compliance.extraction import Extraction
from app.core.config import settings
from app.main import app
from tests.api.routes.test_audits import CAREERS, northwind
from tests.api.routes.test_pay import PricedLLM
from tests.compliance.test_api import MemoryLimits, MemoryUsage
from tests.compliance.test_employer import MemorySizes
from tests.compliance.test_inspector import extraction, labels

API = settings.API_V1_STR


@pytest.fixture
def env() -> Generator[dict[str, Any]]:
    fake, web, limits, usage = PricedLLM(), northwind(), MemoryLimits(per_week=1), MemoryUsage()
    app.dependency_overrides[get_llm] = fake.fresh
    app.dependency_overrides[get_posting_date] = lambda: date(2026, 10, 23)
    app.dependency_overrides[get_sample_limits] = lambda: limits
    app.dependency_overrides[get_usage] = lambda: usage
    app.dependency_overrides[get_sizes] = MemorySizes
    app.dependency_overrides[rate_limited] = lambda: None
    app.dependency_overrides[get_fetcher] = lambda: web.fetcher()
    store = SampleStore()
    app.dependency_overrides[get_samples] = lambda: store
    yield {"llm": fake, "web": web, "limits": limits, "usage": usage}
    for dependency in (get_llm, get_posting_date, get_sample_limits, get_usage, get_sizes, rate_limited, get_fetcher,
                       get_samples):  # fmt: skip
        app.dependency_overrides.pop(dependency, None)


def start(client: TestClient, url: str = CAREERS) -> Any:
    return client.post(f"{API}/sample-audits/", json={"url": url})


def check(client: TestClient, env: dict[str, Any], sample: dict[str, Any], index: int, queue: bool = True) -> Any:
    if queue:
        env["llm"].queue(Extraction, extraction()).queue(Classification, labels())
    return client.post(f"{API}/sample-audits/{sample['sample_id']}/postings/{index}/check")


def test_the_first_postings_findings_only(client: TestClient, env: dict[str, Any]) -> None:
    response = start(client)
    assert response.status_code == 200, response.text
    sample = response.json()
    assert [(p["title"], p["where"], p["status"]) for p in sample["postings"]] == [
        ("Payroll Specialist", "ontario", "queued"), ("Payroll Specialist", "ontario", "queued"),
        ("Payroll Lead", "canada", "queued"),
    ]  # the first three for Ontario; Calgary left out
    assert (sample["in_ontario"], sample["outside_ontario"]) == (3, 1)
    assert env["limits"].uses == [] and env["llm"].calls == []  # reading the board uses nothing

    first = check(client, env, sample, 0)
    assert first.status_code == 200, first.text
    posting = first.json()
    assert posting["status"] == "not_compliant" and posting["passed"] > 0
    cex = next(f for f in posting["findings"] if f["rule"] == "ON-CEX-01")
    assert cex["verdict"] == "fail" and cex["message"]
    assert "check_id" not in posting and "patches" not in first.text  # findings only: nothing to turn into fixes
    assert len(env["limits"].uses) == 1 and env["limits"].spent > 0  # the week's sample, and the day's spend

    calls = len(env["llm"].calls)
    assert check(client, env, sample, 0, queue=False).json() == posting  # asked again: the same, no new spend
    assert len(env["llm"].calls) == calls
    assert check(client, env, sample, 1).json()["status"] == "not_compliant"
    assert len(env["limits"].uses) == 1  # one sample audit, however many postings
    assert {e["kind"] for e in env["usage"].events} == {"sample_preview", "sample_check"}
    assert client.post(f"{API}/sample-audits/{sample['sample_id']}/postings/3/check").status_code == 404


def test_one_sample_audit_a_week(client: TestClient, env: dict[str, Any]) -> None:
    sample = start(client).json()
    assert start(client).status_code == 200  # nothing checked yet: still free to look
    check(client, env, sample, 0)
    again = start(client)
    assert again.status_code == 429 and again.json()["detail"]["reason"] == "quota"
    assert "free sample audit" in again.json()["detail"]["message"]


def test_our_own_addresses_skip_the_quota(client: TestClient, env: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "FREE_CHECK_ALLOWLIST_IPS", "testclient")
    sample = start(client).json()
    check(client, env, sample, 0)
    assert env["limits"].uses == [] and start(client).status_code == 200


def test_the_daily_spend_cap(client: TestClient, env: dict[str, Any]) -> None:
    sample = start(client).json()
    env["limits"].budget = Decimal(0)
    paused = check(client, env, sample, 0, queue=False)
    assert paused.status_code == 503 and paused.json()["detail"]["reason"] == "paused"
    assert env["limits"].uses == [] and env["llm"].calls == []  # not counted, not checked


def test_boards_that_cant_be_read_or_samples_that_expired(client: TestClient, env: dict[str, Any]) -> None:
    robots = start(client, "https://jobs.smartrecruiters.com/NorthwindLogistics")
    assert robots.status_code == 422 and robots.json()["detail"]["reason"] == "robots"
    assert start(client, "http://localhost:8000/admin").json()["detail"]["reason"] == "blocked"
    assert client.post(f"{API}/sample-audits/unknown/postings/0/check").status_code == 404
    env["web"].pages["northwind.example/careers"] = (200, "<p>No jobs</p>", {})
    empty = start(client)
    assert empty.status_code == 422 and env["limits"].uses == []
