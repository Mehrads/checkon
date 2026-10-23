"""The free-check endpoints, end to end with a scripted LLM (no database needed)."""

from collections.abc import Generator
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

import httpx

from app.api.free_check import RateLimiter, rate_limited
from app.api.posting_link import LinkReader
from app.api.routes.checks import (
    get_limits,
    get_link_limiter,
    get_link_reader,
    get_llm,
    get_posting_date,
    get_sizes,
    get_usage,
)
from app.api.usage import visitor_hash
from app.compliance.classification import Classification
from app.compliance.extraction import Extraction
from app.compliance.form import FormLabels
from app.compliance.normalise import normalise
from app.compliance.refiner import _Rewrite
from app.main import app
from tests.compliance.fake_llm import FakeLLM
from tests.compliance.test_employer import MemorySizes
from tests.compliance.test_inspector import POSTING, extraction, labels
from tests.compliance.test_posting_link import Server, page, redirect, resolver

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
    assert [r["rule"] for r in check["report"]["reminders"]] == ["ON-INT-01", "ON-REC-01"]

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
    assert [r["rule"] for r in final["report"]["reminders"]] == ["ON-INT-01", "ON-REC-01"]
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



# A posting's link: read by the server with no network here (a scripted resolver and a mock transport)

DNS = {"jobs.example.com": ["93.184.216.34"], "internal.example.com": ["10.0.0.7"]}


@pytest.fixture
def site() -> Generator[Server]:
    server = Server({
        "jobs.example.com/payroll": page(POSTING, "text/plain"),
        "jobs.example.com/moved": redirect("http://internal.example.com/payroll"),
        "jobs.example.com/long": page("Payroll duties. " * 600, "text/plain"),
    })  # fmt: skip
    app.dependency_overrides[get_link_reader] = lambda: LinkReader(resolver=resolver(DNS), transport=httpx.MockTransport(server))
    app.dependency_overrides[get_link_limiter] = lambda: limiter
    limiter = RateLimiter(20, window_seconds=3600)
    yield server
    app.dependency_overrides.pop(get_link_reader, None)
    app.dependency_overrides.pop(get_link_limiter, None)


def test_a_posting_link_is_read_and_checked_as_one_check(
    client: TestClient, llm: FakeLLM, limits: MemoryLimits, usage: MemoryUsage, site: Server
) -> None:
    llm.queue(Extraction, extraction()).queue(Classification, labels())
    response = client.post(f"{API}/inspect", json={"url": "https://jobs.example.com/payroll", "meets_headcount_threshold": True})
    assert response.status_code == 200, response.text
    check = response.json()
    assert check["url"] == "https://jobs.example.com/payroll"
    assert check["text"] == normalise(POSTING).text
    assert check["report"]["status"] == "not_compliant"
    assert len(limits.uses) == 1
    assert [e["kind"] for e in usage.events] == ["check"]
    assert "jobs.example.com" not in str(usage.events)  # neither the posting nor its address is kept


@pytest.mark.parametrize(
    ("link", "reason"),
    [
        ("https://www.linkedin.com/jobs/view/123", "blocked_site"),
        ("https://ca.indeed.com/viewjob?jk=1", "blocked_site"),
        ("https://www.glassdoor.ca/job-listing/x", "blocked_site"),
        ("http://169.254.169.254/latest/meta-data/", "unsafe_url"),
        ("http://10.0.0.1/", "unsafe_url"),
        ("http://internal.example.com/", "unsafe_url"),
        ("https://jobs.example.com/moved", "unsafe_url"),  # a redirect to a private address
        ("file:///etc/passwd", "bad_url"),
        ("https://jobs.example.com/missing", "fetch_failed"),
        ("https://jobs.example.com/long", "too_long"),
    ],
)  # fmt: skip
def test_a_link_that_cant_be_read_asks_for_a_paste_and_uses_no_check(
    client: TestClient, llm: FakeLLM, limits: MemoryLimits, usage: MemoryUsage, site: Server, link: str, reason: str
) -> None:
    response = client.post(f"{API}/inspect", json={"url": link})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["reason"] == reason
    assert reason == "bad_url" or "aste the posting" in detail["message"] or "aste just the posting" in detail["message"]
    assert llm.calls == [] and limits.uses == []
    assert [(e["kind"], e["status"]) for e in usage.events] == [("refused", reason)]
    assert all(request.headers["host"] == "jobs.example.com" for request in site.requests)


def test_links_are_rate_limited_per_address(client: TestClient, llm: FakeLLM, site: Server) -> None:
    app.dependency_overrides[get_link_limiter] = lambda: limiter
    limiter = RateLimiter(2, window_seconds=3600)
    for _ in range(2):
        assert client.post(f"{API}/inspect", json={"url": "https://jobs.example.com/missing"}).status_code == 422
    response = client.post(f"{API}/inspect", json={"url": "https://jobs.example.com/missing"})
    assert response.status_code == 429
    assert response.json()["detail"]["reason"] == "fetch_limit"
    assert len(site.requests) == 2


def test_a_visitor_with_no_check_left_makes_no_fetch(
    client: TestClient, llm: FakeLLM, limits: MemoryLimits, site: Server
) -> None:
    limits.per_week = 1
    inspect(client, llm)
    response = client.post(f"{API}/inspect", json={"url": "https://jobs.example.com/payroll"})
    assert response.status_code == 429 and response.json()["detail"]["reason"] == "quota"
    assert site.requests == []


@pytest.mark.parametrize("body", [{}, {"text": POSTING, "url": "https://jobs.example.com/payroll"}, {"url": ""}])
def test_inspect_takes_text_or_a_link(client: TestClient, llm: FakeLLM, body: dict) -> None:
    assert client.post(f"{API}/inspect", json=body).status_code == 422
    assert llm.calls == []


# The application form: one more check, on the same limits

FORM = """Email *
Do you have Canadian work experience? *
- Yes
- No
Are you legally entitled to work in Canada?
"""


def inspect_without_canadian_experience(client: TestClient, llm: FakeLLM) -> dict:
    found = labels()
    for label in found["canadian_experience"]:
        label["label"] = "ok"
    llm.queue(Extraction, extraction()).queue(Classification, found)
    return client.post(f"{API}/inspect", json={"text": POSTING, "meets_headcount_threshold": True}).json()


def form_labels(*found: str) -> dict:
    return {"questions": [{"question": n, "label": label, "reason": "r"} for n, label in enumerate(found, start=1)]}


def check_form(client: TestClient, llm: FakeLLM, check_id: str, *found: str, form: str = FORM) -> dict:
    llm.queue(FormLabels, form_labels(*found))
    response = client.post(f"{API}/form", json={"check_id": check_id, "form": form})
    assert response.status_code == 200, response.text
    return response.json()


def test_the_form_is_checked_for_canadian_experience_as_a_second_check(
    client: TestClient, llm: FakeLLM, limits: MemoryLimits, usage: MemoryUsage
) -> None:
    first = inspect_without_canadian_experience(client, llm)
    assert first["form_text"] is None and first["report"]["form_results"] == []

    check = check_form(client, llm, first["check_id"], "ok", "violation", "ok")
    assert verdicts(check["report"])["ON-CEX-01"] == "pass"  # the posting itself
    [result] = check["report"]["form_results"]
    assert (result["rule"], result["verdict"]) == ("ON-CEX-01", "fail")
    assert "application form" in result["message"] and "s. 8.3 (1)" in result["citation"]
    [(start, end)] = result["evidence"]
    assert check["form_text"][start:end] == "Do you have Canadian work experience? *\n- Yes\n- No"
    assert check["report"]["status"] == "not_compliant"
    assert check["report"]["versions"]["form_hash"]
    assert len(limits.uses) == 2  # the posting and the form
    assert [(e["kind"], e.get("count")) for e in usage.events] == [("check", None), ("form", 3)]
    # Only the form task's prompt and questions went to the model; the posting wasn't read again.
    [call] = llm.calls_for(FormLabels)
    assert "Do you have Canadian work experience?" in call.user and "Payroll" not in call.user


def test_the_free_check_covers_the_posting_but_not_the_form(
    client: TestClient, llm: FakeLLM, limits: MemoryLimits
) -> None:
    limits.per_week = 1
    check = inspect(client, llm)
    response = client.post(f"{API}/form", json={"check_id": check["check_id"], "form": FORM})
    assert response.status_code == 429
    assert response.json()["detail"] == {
        "reason": "quota",
        "message": "Checking the application form uses a second check, and you've used this week's free check. "
        "Your next free check is available on October 26.",
    }
    assert llm.calls_for(FormLabels) == []


def test_form_results_last_through_answers_fixes_and_the_final_text(client: TestClient, llm: FakeLLM) -> None:
    check = inspect(client, llm)  # Canadian experience fails in the posting; AI use is asked
    check = check_form(client, llm, check["check_id"], "ok", "violation", "ok")

    check = client.post(f"{API}/answers", json={"check_id": check["check_id"], "answers": {"uses_ai_in_hiring": False}}).json()
    assert [r["verdict"] for r in check["report"]["form_results"]] == ["fail"]

    llm.queue(_Rewrite, {"sentence": "2+ years of payroll experience"})
    llm.queue(Classification, {"canadian_experience": [{"sentence": 4, "label": "ok", "reason": "r"}], "vacancy": [], "ai": []})
    check = client.post(f"{API}/refine", json={"check_id": check["check_id"]}).json()
    assert [p["rule"] for p in check["refinement"]["patches"]] == ["ON-CEX-01"]  # the posting's sentence only
    assert [r["verdict"] for r in check["refinement"]["report"]["form_results"]] == ["fail"]

    final = client.post(f"{API}/patches/accept", json={"check_id": check["check_id"], "decisions": []}).json()
    assert verdicts(final["report"])["ON-CEX-01"] == "pass"
    assert [r["verdict"] for r in final["report"]["form_results"]] == ["fail"]
    assert final["report"]["status"] == "not_compliant"  # the form still asks for Canadian experience


def test_a_form_added_after_the_fixes_updates_them_from_the_cache(client: TestClient, llm: FakeLLM) -> None:
    check = inspect(client, llm)
    llm.queue(_Rewrite, {"sentence": "2+ years of payroll experience"})
    llm.queue(Classification, {"canadian_experience": [{"sentence": 4, "label": "ok", "reason": "r"}], "vacancy": [], "ai": []})
    client.post(f"{API}/refine", json={"check_id": check["check_id"]})
    calls = len(llm.calls)
    check = check_form(client, llm, check["check_id"], "ok", "ok", "ok", form=FORM.replace("Canadian ", ""))
    assert len(llm.calls) == calls + 1  # the form's labels; the rewrite and its labels come from the cache
    assert [r["verdict"] for r in check["refinement"]["report"]["form_results"]] == ["pass"]


def test_an_optional_form_question_is_a_warning(client: TestClient, llm: FakeLLM) -> None:
    first = inspect_without_canadian_experience(client, llm)
    check = check_form(client, llm, first["check_id"], "violation", form="Years of experience in Canada (optional)")
    assert [(r["verdict"], r["message"][:24]) for r in check["report"]["form_results"]] == [
        ("warning", "An optional question in ")
    ]


def test_a_form_without_questions_or_for_an_excluded_posting_uses_no_check(
    client: TestClient, llm: FakeLLM, limits: MemoryLimits
) -> None:
    check = inspect(client, llm)
    response = client.post(f"{API}/form", json={"check_id": check["check_id"], "form": " \n\n "})
    assert response.status_code == 422 and response.json()["detail"]["reason"] == "empty_form"

    llm.queue(Extraction, extraction(internal_only=True)).queue(Classification, labels())
    internal = client.post(f"{API}/inspect", json={"text": POSTING, "meets_headcount_threshold": True}).json()
    assert internal["report"]["status"] == "not_applicable"
    response = client.post(f"{API}/form", json={"check_id": internal["check_id"], "form": FORM})
    assert response.status_code == 422 and response.json()["detail"]["reason"] == "not_applicable"
    assert llm.calls_for(FormLabels) == [] and len(limits.uses) == 2  # the two postings only


def test_the_form_is_capped_and_needs_a_live_check(client: TestClient, llm: FakeLLM) -> None:
    check = inspect(client, llm)
    assert client.post(f"{API}/form", json={"check_id": check["check_id"], "form": "x" * 4001}).status_code == 422
    assert client.post(f"{API}/form", json={"check_id": "expired", "form": FORM}).status_code == 404
