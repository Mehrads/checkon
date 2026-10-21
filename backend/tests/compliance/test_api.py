"""The free-check endpoints, end to end with a scripted LLM (no database needed)."""

from collections.abc import Generator
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.free_check import rate_limited
from app.api.routes.checks import get_limits, get_llm, get_posting_date, get_sizes, get_usage
from app.api.usage import visitor_hash
from app.compliance.classification import Classification
from app.compliance.extraction import Extraction
from app.compliance.refiner import _Rewrite
from app.main import app
from tests.compliance.fake_llm import FakeLLM
from tests.compliance.test_employer import MemorySizes
from tests.compliance.test_inspector import POSTING, extraction, labels

API = "/api/v1"


class MemoryLimits:
    """The free-check limits without Postgres: same rules, kept in a dict."""

    def __init__(self, per_week: int = 1, budget: Decimal = Decimal(5)) -> None:
        self.uses: list[tuple[str, str]] = []
        self.per_week = per_week
        self.budget = budget
        self.spent = Decimal(0)

    def next_free_check(self, cookie: str, ip: str) -> datetime | None:
        hits = [use for use in self.uses if cookie == use[0] or ip == use[1]]
        return datetime(2026, 10, 26, 12, tzinfo=UTC) if len(hits) >= self.per_week else None

    def record_use(self, cookie: str, ip: str) -> None:
        self.uses.append((cookie, ip))

    def budget_left(self) -> bool:
        return self.spent < self.budget

    def add_spend(self, usd: Decimal) -> None:
        self.spent += usd


class MemoryUsage:
    """Usage events without Postgres."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def record(self, kind: str, **fields: Any) -> None:
        self.events.append({"kind": kind, **fields})


@pytest.fixture
def limits() -> MemoryLimits:
    return MemoryLimits(per_week=100)  # most tests run several checks


@pytest.fixture
def usage() -> MemoryUsage:
    return MemoryUsage()


@pytest.fixture
def llm(limits: MemoryLimits, usage: MemoryUsage) -> Generator[FakeLLM]:
    fake = FakeLLM()
    app.dependency_overrides[get_llm] = lambda: fake
    app.dependency_overrides[get_posting_date] = lambda: date(2026, 10, 19)
    app.dependency_overrides[get_limits] = lambda: limits
    app.dependency_overrides[get_usage] = lambda: usage
    app.dependency_overrides[get_sizes] = MemorySizes
    app.dependency_overrides[rate_limited] = lambda: None
    yield fake
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def inspect(client: TestClient, llm: FakeLLM) -> dict:
    llm.queue(Extraction, extraction()).queue(Classification, labels())
    response = client.post(f"{API}/inspect", json={"text": POSTING, "meets_headcount_threshold": True})
    assert response.status_code == 200, response.text
    return response.json()


def verdicts(report: dict) -> dict[str, str]:
    return {r["rule"]: r["verdict"] for r in report["results"]}


def test_paste_answer_review_and_copy(client: TestClient, llm: FakeLLM) -> None:
    # 1. Inspect: Canadian experience fails, and AI use is unknown, so the check asks.
    check = inspect(client, llm)
    assert check["report"]["status"] == "not_compliant"
    assert [(q["id"], q["kind"]) for q in check["questions"]] == [("uses_ai_in_hiring", "yes_no")]
    canadian = next(r for r in check["report"]["results"] if r["rule"] == "ON-CEX-01")["evidence"][0]
    assert check["text"][canadian[0] : canadian[1]] == "2+ years of Canadian payroll experience"

    # 2. Refine: the Canadian-experience sentence is rewritten and re-read.
    llm.queue(_Rewrite, {"sentence": "2+ years of payroll experience"})
    llm.queue(Classification, {"canadian_experience": [{"sentence": 4, "label": "ok", "reason": "r"}], "vacancy": [], "ai": []})
    check = client.post(f"{API}/refine", json={"check_id": check["check_id"]}).json()
    assert [p["rule"] for p in check["refinement"]["patches"]] == ["ON-CEX-01"]

    # 3. Answer: AI is used, so a disclosure patch appears; the rewrite comes from the cache.
    calls = len(llm.calls)
    check = client.post(f"{API}/answers", json={"check_id": check["check_id"], "answers": {"uses_ai_in_hiring": True}}).json()
    assert len(llm.calls) == calls  # no LLM call to answer a question
    assert verdicts(check["report"])["ON-AI-01"] == "fail"
    assert [p["rule"] for p in check["refinement"]["patches"]] == ["ON-AI-01", "ON-CEX-01"]
    assert check["questions"] == []

    # 4. Accept: reject nothing; the final text keeps the pasted characters outside the patches.
    final = client.post(f"{API}/patches/accept", json={"check_id": check["check_id"], "decisions": []}).json()
    assert final["report"]["status"] == "compliant"
    assert "• 2+ years of payroll experience" in final["text"]
    assert "$60,000 – $80,000 per year" in final["text"]
    assert "We use artificial intelligence to screen, assess or select applicants" in final["text"]


def test_rejecting_a_patch_keeps_its_finding(client: TestClient, llm: FakeLLM) -> None:
    check = inspect(client, llm)
    llm.queue(_Rewrite, {"sentence": "2+ years of payroll experience"})
    llm.queue(Classification, {"canadian_experience": [{"sentence": 4, "label": "ok", "reason": "r"}], "vacancy": [], "ai": []})
    check = client.post(f"{API}/refine", json={"check_id": check["check_id"]}).json()
    patch_id = check["refinement"]["patches"][0]["id"]

    decisions = [{"patch_id": patch_id, "accept": False}]
    final = client.post(f"{API}/patches/accept", json={"check_id": check["check_id"], "decisions": decisions}).json()
    assert verdicts(final["report"])["ON-CEX-01"] == "fail"
    assert final["text"] == POSTING


def test_refused_input_returns_the_reason(client: TestClient, llm: FakeLLM) -> None:
    llm.queue(Extraction, extraction(input_kind="multiple_postings"))
    response = client.post(f"{API}/inspect", json={"text": POSTING})
    assert response.status_code == 422
    assert response.json()["detail"]["reason"] == "multiple_postings"


def test_posting_length_is_capped(client: TestClient, llm: FakeLLM) -> None:
    response = client.post(f"{API}/inspect", json={"text": "x" * 8001})
    assert response.status_code == 422
    assert llm.calls == []


def test_unknown_check_is_not_found(client: TestClient, llm: FakeLLM) -> None:
    assert client.post(f"{API}/refine", json={"check_id": "nope"}).status_code == 404


def test_accept_before_refine_is_a_conflict(client: TestClient, llm: FakeLLM) -> None:
    check = inspect(client, llm)
    response = client.post(f"{API}/patches/accept", json={"check_id": check["check_id"]})
    assert response.status_code == 409


def test_model_failure_is_a_bad_gateway(client: TestClient, llm: FakeLLM) -> None:
    from app.compliance.llm import LLMError

    llm.queue(Extraction, LLMError("declined"))
    response = client.post(f"{API}/inspect", json={"text": POSTING})
    assert response.status_code == 502


def test_missing_api_key_is_service_unavailable(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", None)
    response = client.post(f"{API}/inspect", json={"text": POSTING})
    assert response.status_code == 503


# Free-check limits


def test_second_check_in_a_week_is_refused(client: TestClient, llm: FakeLLM, limits: MemoryLimits) -> None:
    limits.per_week = 1
    first = inspect(client, llm)
    assert first["research_question"]["options"]
    response = client.post(f"{API}/inspect", json={"text": POSTING})
    assert response.status_code == 429
    assert response.json()["detail"] == {
        "reason": "quota",
        "message": "You've used this week's free check. Your next free check is available on October 26.",
    }
    assert len(limits.uses) == 1


def test_allowlisted_ip_skips_the_quota_but_not_the_spend_cap(
    client: TestClient, llm: FakeLLM, limits: MemoryLimits, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api import free_check

    monkeypatch.setattr(free_check.settings, "FREE_CHECK_ALLOWLIST_IPS", " 203.0.113.9, testclient ")  # the TestClient's address
    limits.per_week = 1
    limits.uses.append(("someone-else", "testclient"))  # this address already used its week's check
    inspect(client, llm)
    inspect(client, llm)
    assert limits.uses == [("someone-else", "testclient")]  # nothing recorded against the allowlisted visitor
    limits.spent = limits.budget
    llm.queue(Extraction, extraction()).queue(Classification, labels())
    response = client.post(f"{API}/inspect", json={"text": POSTING})
    assert response.status_code == 503 and response.json()["detail"]["reason"] == "paused"


def test_visitor_cookie_is_set_and_reused(client: TestClient, llm: FakeLLM, limits: MemoryLimits) -> None:
    inspect(client, llm)
    cookie = client.cookies.get("free_check_id")
    assert cookie
    inspect(client, llm)
    assert [use[0] for use in limits.uses] == [cookie, cookie]


def test_refused_input_uses_no_credit(client: TestClient, llm: FakeLLM, limits: MemoryLimits) -> None:
    llm.queue(Extraction, extraction(input_kind="not_a_posting"))
    assert client.post(f"{API}/inspect", json={"text": POSTING}).status_code == 422
    assert limits.uses == []


def test_daily_spend_cap_pauses_free_checks(client: TestClient, llm: FakeLLM, limits: MemoryLimits) -> None:
    limits.spent = limits.budget
    response = client.post(f"{API}/inspect", json={"text": POSTING})
    assert response.status_code == 503
    assert response.json()["detail"]["reason"] == "paused"
    assert llm.calls == []


def test_metered_spend_is_recorded(client: TestClient, llm: FakeLLM, limits: MemoryLimits) -> None:
    from app.compliance.llm import SpendMeter

    llm.meter = SpendMeter()  # type: ignore[attr-defined]
    llm.meter.add("claude-haiku-5-5", 10_000, 2_000)  # what the calls would report
    inspect(client, llm)
    assert limits.spent == Decimal("0.002")


def test_other_sites_cannot_call_the_api(client: TestClient, llm: FakeLLM) -> None:
    response = client.post(f"{API}/inspect", json={"text": POSTING}, headers={"Origin": "https://evil.example"})
    assert response.status_code == 403
    assert response.json()["detail"]["reason"] == "origin"


def test_only_allowed_extensions_can_call_the_api(
    client: TestClient, llm: FakeLLM, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "EXTENSION_IDS", "lfepfedddcabkigmmhbhacdllgljpdbe, other")
    allowed = client.post(f"{API}/refine", json={"check_id": "nope"}, headers={"Origin": "chrome-extension://lfepfedddcabkigmmhbhacdllgljpdbe"})
    assert allowed.status_code == 404  # past the origin check
    edge = client.post(f"{API}/refine", json={"check_id": "nope"}, headers={"Origin": "extension://other"})
    assert edge.status_code == 404
    stranger = client.post(f"{API}/refine", json={"check_id": "nope"}, headers={"Origin": "chrome-extension://someoneelse"})
    assert stranger.status_code == 403
    assert stranger.json()["detail"]["reason"] == "origin"


def test_client_ip_reads_the_proxy_hop_not_the_client_supplied_header(monkeypatch: pytest.MonkeyPatch) -> None:
    from starlette.requests import Request

    from app.api.free_check import client_ip
    from app.core.config import settings

    def request(forwarded: str | None) -> Request:
        headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
        return Request({"type": "http", "headers": headers, "client": ("10.0.0.1", 1234)})

    assert client_ip(request("1.2.3.4")) == "10.0.0.1"  # proxies not trusted by default
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 1)
    assert client_ip(request("6.6.6.6, 203.0.113.5")) == "203.0.113.5"  # the spoofed first entry is ignored
    assert client_ip(request(None)) == "10.0.0.1"


def test_same_host_origin_is_allowed_over_http_behind_a_proxy(client: TestClient, llm: FakeLLM) -> None:
    # Cloud Run serves HTTPS to the browser but plain HTTP to the app; the hosts still match.
    response = client.post(f"{API}/refine", json={"check_id": "nope"}, headers={"Origin": "https://testserver"})
    assert response.status_code == 404  # past the origin check


# Usage events (the admin Stats page)


def test_each_step_is_recorded_for_the_usage_stats(client: TestClient, llm: FakeLLM, usage: MemoryUsage) -> None:
    check = inspect(client, llm)
    llm.queue(_Rewrite, {"sentence": "2+ years of payroll experience"})
    llm.queue(Classification, {"canadian_experience": [{"sentence": 4, "label": "ok", "reason": "r"}], "vacancy": [], "ai": []})
    client.post(f"{API}/refine", json={"check_id": check["check_id"]})
    client.post(f"{API}/patches/accept", json={"check_id": check["check_id"], "decisions": []})

    assert [(e["kind"], e.get("status"), e.get("count")) for e in usage.events] == [
        ("check", "not_compliant", None), ("refine", "ok", None), ("accept", None, 1),
    ]
    assert {e["check_id"] for e in usage.events} == {check["check_id"]}
    assert usage.events[0]["visitor"] == visitor_hash(client.cookies["free_check_id"])
    assert all(e["duration_ms"] >= 0 for e in usage.events)
    assert "payroll" not in str(usage.events)  # never the posting text


def test_refusals_are_recorded_for_the_same_visitor(
    client: TestClient, llm: FakeLLM, limits: MemoryLimits, usage: MemoryUsage
) -> None:
    limits.per_week = 1
    llm.queue(Extraction, extraction(input_kind="not_a_posting"))
    assert client.post(f"{API}/inspect", json={"text": POSTING}).status_code == 422
    inspect(client, llm)
    assert client.post(f"{API}/inspect", json={"text": POSTING}).status_code == 429

    assert [(e["kind"], e.get("status")) for e in usage.events] == [
        ("refused", "not_a_posting"), ("check", "not_compliant"), ("quota", None),
    ]
    # An error response can't set the cookie, so only the check and the later try share a visitor.
    assert usage.events[1]["visitor"] == usage.events[2]["visitor"]
