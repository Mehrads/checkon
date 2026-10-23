"""The free sample audit on the public site: a visitor enters a careers page or job board, and the first few open
Ontario postings on it are checked, findings only. It shows what a paid audit finds; the fixes come with a plan.

Each sample costs model fees, so it has the free check's limits: a weekly quota per cookie and per IP (its own,
SAMPLE_AUDITS_PER_WEEK), the same daily spend cap, rate limit, origin check and allowlist. The quota is used when
the first posting is checked, not when the board is read. Nothing is stored: the board and the results stay in
memory for an hour, and no check is kept, so there is nothing to refine into fixes.
"""

import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.api.deps import SessionDep
from app.api.free_check import (
    Limits,
    PostgresLimits,
    client_ip,
    quota_exempt,
    rate_limited,
    refused,
    same_origin,
    visitor_cookie,
)
from app.api.routes.audits import (
    MAX_POSTING_CHARS,
    FetcherDep,
    PostingStatus,
    Where,
    _address,
    _fetch_failure,
)
from app.api.routes.checks import (
    TORONTO,
    DateDep,
    LLMDep,
    PackDep,
    SizesDep,
    UsageDep,
    _spent,
    get_posting_date,
)
from app.api.usage import elapsed_ms, visitor_hash
from app.audit.boards import Board, Found, Source, posting_text, read_board
from app.audit.fetch import Fetcher, FetchError
from app.compliance.employer import SizeCache
from app.compliance.inspector import InputRefused, inspect
from app.compliance.llm import LLMError, StructuredLLM
from app.compliance.models import Context, Verdict
from app.compliance.rulepack import RulePack
from app.core.config import settings

router = APIRouter(
    prefix="/sample-audits", tags=["audits"], dependencies=[Depends(rate_limited), Depends(same_origin)]
)

_ORDER = {Verdict.FAIL: 0, Verdict.WARNING: 1, Verdict.NEEDS_INPUT: 2}


class Finding(BaseModel):
    rule: str
    verdict: Verdict
    message: str


class SamplePosting(BaseModel):
    index: int
    title: str
    location: str | None
    url: str
    where: Where
    status: PostingStatus
    findings: list[Finding] = []  # the rules to act on: fails, then warnings, then questions
    passed: int = 0  # rules the posting meets
    note: str | None = None  # why it wasn't checked


class SampleIn(BaseModel):
    url: str = Field(min_length=3, max_length=2048)


class SampleOut(BaseModel):
    sample_id: str
    url: str  # the page that was read
    source: Source
    board_name: str | None
    postings: list[SamplePosting]  # the first open postings for Ontario, checked one request each
    in_ontario: int  # open postings in Ontario or Canada-wide on the board
    outside_ontario: int


# In memory for an hour


@dataclass
class Sample:
    board: Board
    postings: list[Found]
    visitor: str  # the visitor's hashed cookie, for the usage records
    results: dict[int, SamplePosting] = field(default_factory=dict)
    checking: set[int] = field(default_factory=set)
    started: bool = False  # the weekly quota was used
    lock: threading.Lock = field(default_factory=threading.Lock)
    id: str = field(default_factory=lambda: secrets.token_urlsafe(16))
    created: float = field(default_factory=time.monotonic)


class SampleStore:
    def __init__(self, ttl_seconds: float = 3600, max_samples: int = 500) -> None:
        self.ttl = ttl_seconds
        self.max_samples = max_samples
        self._samples: dict[str, Sample] = {}
        self._lock = threading.Lock()

    def add(self, sample: Sample) -> Sample:
        with self._lock:
            self._expire()
            while len(self._samples) >= self.max_samples:
                self._samples.pop(next(iter(self._samples)))
            self._samples[sample.id] = sample
        return sample

    def get(self, sample_id: str) -> Sample | None:
        with self._lock:
            self._expire()
            return self._samples.get(sample_id)

    def _expire(self) -> None:
        cutoff = time.monotonic() - self.ttl
        self._samples = {key: sample for key, sample in self._samples.items() if sample.created > cutoff}


_samples = SampleStore()


def get_samples() -> SampleStore:
    return _samples


def get_sample_limits(session: SessionDep, today: Annotated[date, Depends(get_posting_date)]) -> Limits:
    return PostgresLimits(
        session, today, settings.SAMPLE_AUDITS_PER_WEEK, settings.FREE_CHECK_DAILY_SPEND_CAP_USD, settings.SECRET_KEY,
        scope="sample-",
    )  # fmt: skip


SamplesDep = Annotated[SampleStore, Depends(get_samples)]
SampleLimitsDep = Annotated[Limits, Depends(get_sample_limits)]


def _quota_left(limits: Limits, cookie: str, ip: str) -> None:
    if not quota_exempt(ip) and (next_sample := limits.next_free_check(cookie, ip)) is not None:
        day = next_sample.astimezone(TORONTO).strftime("%B %-d")
        raise refused(429, "quota", f"You've used this week's free sample audit. Your next one is available on {day}.")


def _posting(index: int, found: Found, **result: Any) -> SamplePosting:
    return SamplePosting(
        index=index, title=found.title, location=found.location, url=found.url, where=cast(Where, found.where),
        **result,
    )  # fmt: skip


@router.post("/", response_model=SampleOut)
def start_sample(
    body: SampleIn, request: Request, response: Response, samples: SamplesDep, limits: SampleLimitsDep,
    fetcher: FetcherDep, today: DateDep, usage: UsageDep,
) -> Any:  # fmt: skip
    """Read the board and pick its first open postings for Ontario. Nothing is checked or counted yet."""
    started = time.monotonic()
    cookie, ip = visitor_cookie(request, response), client_ip(request)
    _quota_left(limits, cookie, ip)
    try:
        board = read_board(_address(body.url), fetcher, today)
    except FetchError as error:
        usage.record("sample_preview", visitor=visitor_hash(cookie), status="failed", duration_ms=elapsed_ms(started))
        raise _fetch_failure(error)
    ontario = [p for p in board.postings if p.where == "ontario"] + [p for p in board.postings if p.where == "canada"]
    sample = samples.add(Sample(board, ontario[: settings.SAMPLE_AUDIT_POSTINGS], visitor_hash(cookie)))
    usage.record(
        "sample_preview", visitor=sample.visitor, status=board.source, count=len(ontario), duration_ms=elapsed_ms(started)
    )
    return SampleOut(
        sample_id=sample.id, url=board.url, source=board.source, board_name=board.name,
        postings=[_posting(i, found, status="queued") for i, found in enumerate(sample.postings)],
        in_ontario=len(ontario), outside_ontario=len(board.postings) - len(ontario),
    )  # fmt: skip


@router.post("/{sample_id}/postings/{index}/check", response_model=SamplePosting)
def check_sample_posting(
    sample_id: str, index: int, request: Request, response: Response, samples: SamplesDep, limits: SampleLimitsDep,
    fetcher: FetcherDep, llm: LLMDep, pack: PackDep, today: DateDep, sizes: SizesDep, usage: UsageDep,
) -> Any:  # fmt: skip
    """Check one of the sample's postings, findings only. The first one uses the week's sample audit."""
    started = time.monotonic()
    sample = samples.get(sample_id)
    if sample is None or not 0 <= index < len(sample.postings):
        raise HTTPException(status_code=404, detail="This sample has expired. Enter the address again.")
    found = sample.postings[index]
    cookie, ip = visitor_cookie(request, response), client_ip(request)
    with sample.lock:
        if (done := sample.results.get(index)) is not None:
            return done
        if index in sample.checking:
            raise refused(409, "busy", "This posting is being checked.")
        if not sample.started:
            _quota_left(limits, cookie, ip)
        if not limits.budget_left():
            usage.record("paused", visitor=sample.visitor)
            raise refused(503, "paused", "Free checks are paused for the rest of today. Try again tomorrow.")
        if not sample.started:
            if not quota_exempt(ip):
                limits.record_use(cookie, ip)
            sample.started = True
        sample.checking.add(index)

    try:
        result = _check(sample, found, fetcher, llm, pack, today, sizes)
    finally:
        limits.add_spend(_spent(llm))  # the free checks' daily spend
        with sample.lock:
            sample.checking.discard(index)
    usage.record(
        "sample_check", visitor=sample.visitor, status=result["status"], duration_ms=elapsed_ms(started), usd=_spent(llm)
    )
    with sample.lock:
        sample.results[index] = _posting(index, found, **result)
        return sample.results[index]


def _check(
    sample: Sample, found: Found, fetcher: Fetcher, llm: StructuredLLM, pack: RulePack, today: date, sizes: SizeCache
) -> dict[str, Any]:
    """The posting's findings, or why it wasn't checked."""
    try:
        text = found.text or posting_text(sample.board.source, sample.board.key, found.id, found.url, fetcher, today)
    except FetchError as error:
        return {"status": "failed", "note": str(error)[:255]}
    if len(text) > MAX_POSTING_CHARS:
        return {"status": "refused", "note": f"Over {MAX_POSTING_CHARS:,} characters: too long to check here."}
    try:
        report = inspect(text, Context(), today, pack, llm, sizes=sizes).report
    except InputRefused as error:
        return {"status": "refused", "note": error.message}
    except LLMError:
        return {"status": "failed", "note": "We couldn't check this posting right now."}
    to_act = sorted((r for r in report.results if r.verdict in _ORDER), key=lambda r: _ORDER[r.verdict])
    return {
        "status": report.status.value,
        "findings": [Finding(rule=r.rule, verdict=r.verdict, message=r.message) for r in to_act],
        "passed": sum(r.verdict == Verdict.PASS for r in report.results),
    }
