"""The free-check endpoints, end to end with a scripted LLM (no database needed)."""

from collections.abc import Generator
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.api.routes.checks import get_llm, get_posting_date
from app.compliance.classification import Classification
from app.compliance.extraction import Extraction
from app.compliance.refiner import _Rewrite
from app.main import app
from tests.compliance.fake_llm import FakeLLM
from tests.compliance.test_inspector import POSTING, extraction, labels

API = "/api/v1"


@pytest.fixture
def llm() -> Generator[FakeLLM]:
    fake = FakeLLM()
    app.dependency_overrides[get_llm] = lambda: fake
    app.dependency_overrides[get_posting_date] = lambda: date(2026, 10, 19)
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
