"""The employer-size search cache in Postgres (run `docker compose up -d db` and migrate first)."""

import secrets
from collections.abc import Generator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, delete, select

from app.api.employer_cache import KEPT, PostgresSizeCache
from app.api.free_check import rate_limited
from app.api.routes.checks import get_limits, get_llm, get_posting_date, get_usage
from app.compliance.classification import Classification
from app.compliance.employer import EmployerSize
from app.compliance.extraction import Extraction
from app.core.config import settings
from app.core.db import engine
from app.main import app
from app.models import EmployerSizeSearch, get_datetime_utc
from tests.compliance.fake_llm import FakeLLM
from tests.compliance.test_api import MemoryLimits, MemoryUsage
from tests.compliance.test_employer import size
from tests.compliance.test_inspector import POSTED, POSTING, extraction, labels

API = settings.API_V1_STR


@pytest.fixture
def employer(db: Session) -> Generator[str]:
    """A made-up employer, so runs don't see each other's rows; its rows are deleted afterwards."""
    name = f"Maple Leaf {secrets.token_hex(4)} Ltd."
    yield name
    db.exec(delete(EmployerSizeSearch).where(col(EmployerSizeSearch.employer) == name.lower()))
    db.commit()


def rows(db: Session, employer: str) -> list[EmployerSizeSearch]:
    return list(db.exec(select(EmployerSizeSearch).where(EmployerSizeSearch.employer == employer.lower())).all())


def test_a_search_outlives_the_session_that_stored_it(db: Session, employer: str) -> None:
    key = (employer.lower(), "mississauga on")
    found = size(total_employees_min=2000, total_employees_max=2000)
    PostgresSizeCache(db).put(key, found)
    with Session(engine) as fresh:  # as after a cold start or a deploy
        assert PostgresSizeCache(fresh).get(key) == found
        assert PostgresSizeCache(fresh).get((employer.lower(), "ottawa on")) is None


def test_a_new_search_replaces_the_old_one(db: Session, employer: str) -> None:
    key, cache = (employer.lower(), ""), PostgresSizeCache(db)
    cache.put(key, size(summary="about 2,000 employees"))
    cache.put(key, size(summary="about 2,500 employees"))
    assert cache.get(key) == size(summary="about 2,500 employees")
    assert len(rows(db, employer)) == 1


def test_searches_older_than_30_days_are_ignored_then_deleted(db: Session, employer: str) -> None:
    old = get_datetime_utc() - KEPT - timedelta(minutes=1)
    stale = size().model_dump(mode="json")
    db.add(EmployerSizeSearch(employer=employer.lower(), location="old", size=stale, searched_at=old))
    db.commit()
    cache = PostgresSizeCache(db)
    assert cache.get((employer.lower(), "old")) is None
    cache.put((employer.lower(), "new"), size())
    assert [row.location for row in rows(db, employer)] == ["new"]


def test_a_row_from_an_older_shape_is_searched_again(db: Session, employer: str) -> None:
    db.add(EmployerSizeSearch(employer=employer.lower(), location="", size={"found": True}))
    db.commit()
    assert PostgresSizeCache(db).get((employer.lower(), "")) is None


def test_names_longer_than_the_column_are_not_cached(db: Session) -> None:
    key = ("x" * 300, "")
    PostgresSizeCache(db).put(key, size())
    assert PostgresSizeCache(db).get(key) is None


@pytest.fixture
def llm() -> Generator[FakeLLM]:
    """The free check with a scripted LLM and in-memory limits; only the employer cache is in Postgres."""
    fake = FakeLLM()
    overrides = {
        get_llm: lambda: fake, get_posting_date: lambda: POSTED, get_limits: lambda: MemoryLimits(per_week=100),
        get_usage: MemoryUsage, rate_limited: lambda: None,
    }  # fmt: skip
    app.dependency_overrides.update(overrides)
    yield fake
    for dependency in overrides:
        app.dependency_overrides.pop(dependency, None)


def test_the_free_check_searches_once_and_keeps_no_posting_text(
    client: TestClient, db: Session, llm: FakeLLM, employer: str
) -> None:
    text = POSTING + f"\n{employer} is an equal opportunity employer.\n"
    found = size(total_employees_min=2000, total_employees_max=2000)
    llm.queue(EmployerSize, found)
    for _ in range(2):
        llm.queue(Extraction, extraction(employer=employer)).queue(Classification, labels())
        response = client.post(f"{API}/inspect", json={"text": text})
        assert response.status_code == 200, response.text
        appl = next(r for r in response.json()["report"]["results"] if r["rule"] == "ON-APPL-01")
        assert appl["message"].startswith(f"{employer}: about 2,000 employees worldwide (mapleleaf.example).")
    assert len(llm.calls_for(EmployerSize)) == 1
    [row] = rows(db, employer)
    assert (row.employer, row.location) == (employer.lower(), "mississauga on")
    assert row.size == found.model_dump(mode="json")  # the search's figures, summary and source only
