"""Careers page audits for paying customers (PRD FR13): enter a careers page or job board address, see its open
Ontario postings and how many checks they will use, then check them all for the current workspace.

The browser checks the postings one request at a time (a few at once): Cloud Run gives the app CPU only while a
request runs, and a closed tab simply leaves the rest unchecked and uncharged. Each posting checked counts against
the plan like a pasted one. The report keeps each posting's title, place, link and result; the posting text is read
from the board when it's checked and held in memory for an hour, as a pasted posting's is, never in the database.
"""

import secrets
import threading
import time
import uuid
from collections.abc import Generator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, col, func, select

from app.api.billing import (
    PlanAccess,
    PlanLimits,
    allowance,
    plan_access,
    report_extra_checks_later,
)
from app.api.check_store import CheckState
from app.api.deps import CurrentUser, SessionDep
from app.api.free_check import rate_limited, refused, same_origin
from app.api.routes.checks import (
    CheckOut,
    DateDep,
    LLMDep,
    MeterDep,
    PackDep,
    SizesDep,
    StoreDep,
    UsageDep,
    _out,
    _plan_check_allowed,
    _spent,
)
from app.api.usage import elapsed_ms
from app.api.workspaces import current_workspace, label, profile_context, wording
from app.audit.boards import Board, Found, Source, posting_text, read_board
from app.audit.fetch import Blocked, Fetcher, FetchError, RobotsRefused, Unavailable
from app.compliance.inspector import InputRefused, inspect
from app.compliance.llm import LLMError
from app.compliance.models import Context, Status, Verdict
from app.core.config import settings
from app.models import Audit, AuditPosting, PaidCheck, Workspace, get_datetime_utc

MAX_POSTINGS = 50  # checked in one audit
MAX_LISTED = 300  # postings listed from one board
MAX_POSTING_CHARS = 20_000  # a board posting is longer than a pasted one: the board's own text around it
CHECKS_AT_ONCE = 3  # postings of one audit checked at the same time
STALE = timedelta(minutes=5)  # a check that started this long ago and never finished can run again
TTL = 3600.0  # seconds a preview and the postings' text stay in memory

router = APIRouter(prefix="/audits", tags=["audits"], dependencies=[Depends(same_origin)])


# What's held in memory for an hour: the board read for a preview, and the postings' text once the audit starts


@dataclass
class Preview:
    customer_id: uuid.UUID
    workspace_id: uuid.UUID
    url: str  # the address the customer entered
    board: Board
    id: str = field(default_factory=lambda: secrets.token_urlsafe(16))
    created: float = field(default_factory=time.monotonic)


class AuditMemory:
    def __init__(self, ttl_seconds: float = TTL, max_items: int = 200) -> None:
        self.ttl = ttl_seconds
        self.max_items = max_items
        self._previews: dict[str, Preview] = {}
        self._texts: dict[uuid.UUID, tuple[float, dict[str, str]]] = {}
        self._lock = threading.Lock()

    def _expire(self) -> None:
        cutoff = time.monotonic() - self.ttl
        self._previews = {key: p for key, p in self._previews.items() if p.created > cutoff}
        self._texts = {key: value for key, value in self._texts.items() if value[0] > cutoff}
        while len(self._previews) > self.max_items:
            self._previews.pop(next(iter(self._previews)))
        while len(self._texts) > self.max_items:
            self._texts.pop(next(iter(self._texts)))

    def add_preview(self, preview: Preview) -> Preview:
        with self._lock:
            self._expire()
            self._previews[preview.id] = preview
        return preview

    def take_preview(self, preview_id: str) -> Preview | None:
        with self._lock:
            self._expire()
            return self._previews.pop(preview_id, None)

    def keep_texts(self, audit_id: uuid.UUID, texts: dict[str, str]) -> None:
        with self._lock:
            self._expire()
            self._texts[audit_id] = (time.monotonic(), texts)

    def text(self, audit_id: uuid.UUID, posting: str) -> str | None:
        with self._lock:
            self._expire()
            found = self._texts.get(audit_id)
            return found[1].get(posting) if found else None


_memory = AuditMemory()


def get_memory() -> AuditMemory:
    return _memory


def get_fetcher() -> Generator[Fetcher]:
    fetcher = Fetcher()
    try:
        yield fetcher
    finally:
        fetcher.client.close()


def get_audit_access(session: SessionDep, user: CurrentUser) -> PlanAccess:
    access = plan_access(session, user)
    if access is None:
        raise HTTPException(status_code=403, detail="Careers page audits come with a paid plan.")
    return access


MemoryDep = Annotated[AuditMemory, Depends(get_memory)]
FetcherDep = Annotated[Fetcher, Depends(get_fetcher)]
AccessDep = Annotated[PlanAccess, Depends(get_audit_access)]


# The API's shapes

Where = Literal["ontario", "canada"]
PostingStatus = Literal[
    "queued", "checking", "compliant", "not_compliant", "needs_input", "not_applicable", "refused", "failed"
]


class PreviewIn(BaseModel):
    url: str = Field(min_length=3, max_length=2048)
    workspace_id: uuid.UUID | None = None  # Agency: the client workspace picked in the switcher


class FoundPublic(BaseModel):
    id: str
    title: str
    location: str | None
    url: str
    where: Where  # in Ontario, or anywhere in Canada (which may be filled in Ontario)


class PreviewOut(BaseModel):
    preview_id: str
    url: str  # the page that was read
    source: Source
    board_name: str | None
    workspace_id: uuid.UUID
    workspace_name: str
    postings: list[FoundPublic]  # open postings for work in Ontario first, then Canada-wide ones
    more: int  # postings in Ontario or Canada-wide beyond the ones listed
    outside_ontario: int  # postings for work elsewhere, left out
    max_postings: int  # the most one audit checks
    checks_left: int  # the plan's checks left this period, before extra checks
    extra_checks_left: int  # extra checks left this period, billed per check


class StartIn(BaseModel):
    preview_id: str = Field(max_length=64)
    posting_ids: list[str] = Field(min_length=1, max_length=MAX_POSTINGS)


class Issue(BaseModel):
    rule: str
    verdict: Verdict


class AuditPostingPublic(BaseModel):
    id: uuid.UUID
    title: str
    location: str | None
    url: str
    where: Where
    status: PostingStatus
    issues: list[Issue]  # the rules to act on: fails, then warnings, then questions
    note: str | None  # why it wasn't checked
    checked_at: datetime | None
    check_open: bool  # the full check, with its fixes, is still in memory (an hour after the check)
    final_status: Status | None = None  # after the fixes were applied, if they were


class AuditPublic(BaseModel):
    id: uuid.UUID
    created_at: datetime
    url: str
    source: Source
    board_name: str | None
    workspace_id: uuid.UUID | None
    workspace_name: str | None
    found: int
    outside_ontario: int
    postings: list[AuditPostingPublic]


class AuditSummary(BaseModel):
    id: uuid.UUID
    created_at: datetime
    url: str
    board_name: str | None
    workspace_id: uuid.UUID | None
    workspace_name: str | None
    postings: int
    statuses: dict[str, int]  # postings by status


class AuditsPublic(BaseModel):
    data: list[AuditSummary]
    count: int


def _status(row: AuditPosting) -> PostingStatus:
    stale = row.checked_at is None or row.checked_at < get_datetime_utc() - STALE
    return "failed" if row.status == "checking" and stale else cast(PostingStatus, row.status)


def _posting(row: AuditPosting, store: Any, final: str | None = None) -> AuditPostingPublic:
    status = _status(row)
    note = "The check didn't finish. Check it again." if status == "failed" and row.status == "checking" else row.note
    return AuditPostingPublic(
        id=row.id, title=row.title, location=row.location, url=row.url, where=cast(Where, row.where), status=status,
        issues=[Issue(rule=issue["rule"], verdict=Verdict(issue["verdict"])) for issue in row.issues or []],
        note=note, checked_at=row.checked_at, check_open=bool(row.check_id and store.get(row.check_id)),
        final_status=Status(final) if final else None,
    )  # fmt: skip


def _rows(session: Session, audit: Audit) -> list[AuditPosting]:
    return list(session.exec(
        select(AuditPosting).where(AuditPosting.audit_id == audit.id).order_by(col(AuditPosting.position))
    ).all())  # fmt: skip


def _audit_out(session: Session, audit: Audit, store: Any) -> AuditPublic:
    workspace = session.get(Workspace, audit.workspace_id) if audit.workspace_id else None
    rows = _rows(session, audit)
    checks = [row.check_id for row in rows if row.check_id]
    finals = dict(session.exec(
        select(PaidCheck.check_id, PaidCheck.final_status).where(col(PaidCheck.check_id).in_(checks))
    ).all()) if checks else {}  # fmt: skip
    return AuditPublic(
        id=audit.id, created_at=audit.created_at, url=audit.url, source=cast(Source, audit.source),
        board_name=audit.board_name, workspace_id=audit.workspace_id,
        workspace_name=label(workspace) if workspace else None, found=audit.found,
        outside_ontario=audit.outside_ontario,
        postings=[_posting(row, store, finals.get(row.check_id or "")) for row in rows],
    )  # fmt: skip


def _own_audit(session: Session, user_customer: uuid.UUID | None, audit_id: uuid.UUID) -> Audit:
    audit = session.get(Audit, audit_id)
    if audit is None or user_customer is None or audit.customer_id != user_customer:
        raise HTTPException(status_code=404, detail="Audit not found.")
    return audit


def _fetch_failure(error: FetchError) -> HTTPException:
    reason = (
        "robots" if isinstance(error, RobotsRefused) else "blocked" if isinstance(error, Blocked)
        else "not_found" if isinstance(error, Unavailable) else "fetch"
    )  # fmt: skip
    return refused(422, reason, str(error))


def _address(url: str) -> str:
    url = url.strip()
    return url if "://" in url else f"https://{url}"


# Find the postings, then check them


@router.post("/preview", response_model=PreviewOut, dependencies=[Depends(rate_limited)])
def preview_audit(
    body: PreviewIn, session: SessionDep, access: AccessDep, memory: MemoryDep, fetcher: FetcherDep, today: DateDep,
    usage: UsageDep,
) -> Any:  # fmt: skip
    """The open postings on the board or careers page, for work in Ontario or anywhere in Canada, and the checks
    left in the plan. Nothing is checked or charged yet."""
    started = time.monotonic()
    workspace = current_workspace(session, access, body.workspace_id)
    try:
        board = read_board(_address(body.url), fetcher, today)
    except FetchError as error:
        usage.record("audit_preview", status="failed", duration_ms=elapsed_ms(started), plan=access.plan.id)
        raise _fetch_failure(error)
    ontario = [p for p in board.postings if p.where == "ontario"] + [p for p in board.postings if p.where == "canada"]
    preview = memory.add_preview(Preview(access.customer.id, workspace.id, _address(body.url), board))
    current = allowance(session, access.customer, access.plan, get_datetime_utc())
    usage.record(
        "audit_preview", status=board.source, count=len(ontario), duration_ms=elapsed_ms(started), plan=access.plan.id
    )
    return PreviewOut(
        preview_id=preview.id, url=board.url, source=board.source, board_name=board.name, workspace_id=workspace.id,
        workspace_name=label(workspace),
        postings=[FoundPublic(id=p.id, title=p.title, location=p.location, url=p.url, where=cast(Where, p.where))
                  for p in ontario[:MAX_LISTED]],
        more=max(len(ontario) - MAX_LISTED, 0), outside_ontario=len(board.postings) - len(ontario),
        max_postings=MAX_POSTINGS, checks_left=max(access.plan.checks - current.used, 0),
        extra_checks_left=settings.PLAN_EXTRA_CHECKS_MAX - current.extra,
    )  # fmt: skip


@router.post("/", response_model=AuditPublic, status_code=201)
def start_audit(body: StartIn, session: SessionDep, access: AccessDep, memory: MemoryDep, store: StoreDep) -> Any:
    """Start an audit of the postings picked from a preview. Their checks run one request each, from the browser:
    POST /audits/{id}/postings/{posting_id}/check."""
    preview = memory.take_preview(body.preview_id)
    if preview is None or preview.customer_id != access.customer.id:
        if preview is not None:
            memory.add_preview(preview)
        raise HTTPException(status_code=404, detail="This list of postings has expired. Find the postings again.")
    by_id = {p.id: p for p in preview.board.postings if p.where != "elsewhere"}
    picked: list[Found] = [by_id[posting] for posting in dict.fromkeys(body.posting_ids) if posting in by_id]
    if len(picked) != len(set(body.posting_ids)):
        memory.add_preview(preview)
        raise HTTPException(status_code=422, detail="Some of those postings aren't on this board.")
    current = allowance(session, access.customer, access.plan, get_datetime_utc())
    left = access.plan.checks + settings.PLAN_EXTRA_CHECKS_MAX - current.used
    if len(picked) > left:
        memory.add_preview(preview)
        raise refused(429, "plan_limit", f"You have {max(left, 0)} checks left this billing period. Pick fewer postings.")
    workspace = session.get(Workspace, preview.workspace_id)
    if workspace is None or workspace.customer_id != access.customer.id or workspace.archived_at is not None:
        raise HTTPException(status_code=409, detail="That workspace was archived. Pick another one and try again.")
    board = preview.board
    audit = Audit(
        customer_id=access.customer.id, workspace_id=workspace.id, user_id=access.user.id, url=preview.url[:2048],
        source=board.source, board=board.key[:2048], board_name=(board.name or "")[:255] or None,
        found=len(board.postings), outside_ontario=sum(p.where == "elsewhere" for p in board.postings),
    )  # fmt: skip
    session.add(audit)
    session.flush()
    for position, posting in enumerate(picked):
        session.add(AuditPosting(
            audit_id=audit.id, position=position, external_id=posting.id[:2048], title=posting.title[:255] or "Untitled",
            location=(posting.location or "")[:255] or None, url=posting.url[:2048], where=posting.where,
        ))  # fmt: skip
    session.commit()
    session.refresh(audit)
    memory.keep_texts(audit.id, {p.id: p.text for p in picked if p.text})
    return _audit_out(session, audit, store)


_ORDER = {Verdict.FAIL: 0, Verdict.WARNING: 1, Verdict.NEEDS_INPUT: 2}


def _finish(session: Session, row: AuditPosting, status: str, note: str | None = None) -> None:
    row.status, row.note, row.checked_at = status, note[:255] if note else None, get_datetime_utc()
    session.add(row)
    session.commit()


@router.post("/{audit_id}/postings/{posting_id}/check", response_model=AuditPostingPublic)
def check_posting(
    audit_id: uuid.UUID, posting_id: uuid.UUID, session: SessionDep, access: AccessDep, background: BackgroundTasks,
    memory: MemoryDep, fetcher: FetcherDep, store: StoreDep, llm: LLMDep, pack: PackDep, today: DateDep,
    sizes: SizesDep, usage: UsageDep, meter: MeterDep,
) -> Any:  # fmt: skip
    """Check one posting of the audit against the plan: read it from the board, then check it like a pasted posting
    for the audit's workspace. A posting already checked whose full check is still open isn't checked again."""
    started = time.monotonic()
    audit = _own_audit(session, access.customer.id, audit_id)
    row = session.exec(
        select(AuditPosting).where(AuditPosting.id == posting_id, AuditPosting.audit_id == audit.id).with_for_update()
    ).first()  # fmt: skip
    if row is None:
        raise HTTPException(status_code=404, detail="Posting not found.")
    status = _status(row)
    if status == "checking":
        raise HTTPException(status_code=409, detail="This posting is being checked.")
    if row.check_id and store.get(row.check_id):  # done, and the full check is still open: nothing to redo
        session.commit()
        return _posting(row, store)
    checking = session.exec(
        select(func.count()).select_from(AuditPosting).where(
            AuditPosting.audit_id == audit.id, AuditPosting.status == "checking",
            col(AuditPosting.checked_at) > get_datetime_utc() - STALE,
        )
    ).one()  # fmt: skip
    if checking >= CHECKS_AT_ONCE:
        raise refused(429, "busy", "A few postings are being checked. Try this one in a moment.")
    plan = PlanLimits(session, access)
    _plan_check_allowed(plan, usage)
    row.status, row.note, row.checked_at = "checking", None, get_datetime_utc()
    session.add(row)
    session.commit()  # releases the row: a second request now sees it's being checked

    try:
        text = memory.text(audit.id, row.external_id) or posting_text(
            cast(Source, audit.source), audit.board, row.external_id, row.url, fetcher, today
        )
    except FetchError as error:
        _finish(session, row, "failed", str(error))
        return _posting(row, store)
    if len(text) > MAX_POSTING_CHARS:
        _finish(session, row, "refused", f"Over {MAX_POSTING_CHARS:,} characters: too long to check here.")
        return _posting(row, store)

    workspace = session.get(Workspace, audit.workspace_id) if audit.workspace_id else None
    ctx = profile_context(workspace) if workspace else Context()
    employer = workspace.employer_name if workspace else None
    try:
        inspection = inspect(text, ctx, today, pack, llm, sizes=sizes, employer=employer)
    except InputRefused as error:  # no check used
        usage.record("refused", status=error.reason, duration_ms=elapsed_ms(started), usd=_spent(llm), plan=plan.plan.id)
        _finish(session, row, "refused", error.message)
        return _posting(row, store)
    except LLMError:
        usage.record("failed", duration_ms=elapsed_ms(started), usd=_spent(llm), plan=plan.plan.id)
        _finish(session, row, "failed", "We couldn't check this posting right now. Check it again.")
        return _posting(row, store)
    state = store.add(CheckState(
        posting_date=today, ctx=inspection.context, inspection=inspection, plan=plan.plan.id,
        workspace_id=workspace.id if workspace else None, wording=wording(workspace),
    ))  # fmt: skip
    report = inspection.report
    title = inspection.facts.title.value if inspection.facts.title else row.title
    plan.record(state.id, title, report.status.value, state.workspace_id)
    if meter is not None:  # extra checks go to Stripe's meter after the response
        background.add_task(report_extra_checks_later, meter, plan.customer_id)
    usage.record(
        "check", check_id=state.id, status=report.status.value, duration_ms=elapsed_ms(started), usd=_spent(llm),
        plan=plan.plan.id,
    )  # fmt: skip
    to_act = sorted((r for r in report.results if r.verdict in _ORDER), key=lambda r: _ORDER[r.verdict])
    row.issues = [{"rule": result.rule, "verdict": result.verdict.value} for result in to_act]
    row.check_id = state.id
    _finish(session, row, report.status.value)
    return _posting(row, store)


# The reports


@router.get("/", response_model=AuditsPublic)
def read_audits(
    session: SessionDep, user: CurrentUser, workspace_id: uuid.UUID | None = None, skip: int = 0, limit: int = 20
) -> Any:
    """The customer's audits, newest first, for one workspace or all of them."""
    if user.customer_id is None:
        return AuditsPublic(data=[], count=0)
    mine = [col(Audit.customer_id) == user.customer_id]
    if workspace_id is not None:
        mine.append(col(Audit.workspace_id) == workspace_id)
    count = session.exec(select(func.count()).select_from(Audit).where(*mine)).one()
    audits = session.exec(
        select(Audit).where(*mine).order_by(col(Audit.created_at).desc()).offset(skip).limit(min(limit, 100))
    ).all()
    data = []
    for audit in audits:
        rows = _rows(session, audit)
        statuses: dict[str, int] = {}
        for row in rows:
            statuses[_status(row)] = statuses.get(_status(row), 0) + 1
        workspace = session.get(Workspace, audit.workspace_id) if audit.workspace_id else None
        data.append(AuditSummary(
            id=audit.id, created_at=audit.created_at, url=audit.url, board_name=audit.board_name,
            workspace_id=audit.workspace_id, workspace_name=label(workspace) if workspace else None,
            postings=len(rows), statuses=statuses,
        ))  # fmt: skip
    return AuditsPublic(data=data, count=count)


@router.get("/{audit_id}", response_model=AuditPublic)
def read_audit(audit_id: uuid.UUID, session: SessionDep, user: CurrentUser, store: StoreDep) -> Any:
    return _audit_out(session, _own_audit(session, user.customer_id, audit_id), store)


@router.get("/{audit_id}/postings/{posting_id}", response_model=CheckOut)
def read_posting_check(
    audit_id: uuid.UUID, posting_id: uuid.UUID, session: SessionDep, user: CurrentUser, store: StoreDep
) -> Any:
    """A checked posting's full check, with its findings and fixes, while it's in memory (an hour)."""
    audit = _own_audit(session, user.customer_id, audit_id)
    row = session.get(AuditPosting, posting_id)
    if row is None or row.audit_id != audit.id or row.check_id is None:
        raise HTTPException(status_code=404, detail="This posting hasn't been checked.")
    state = store.get(row.check_id)
    if state is None:  # not cached: browsers may otherwise keep a 410 and miss the check run again
        raise HTTPException(
            status_code=410, headers={"Cache-Control": "no-store"},
            detail={"reason": "expired",
                    "message": "This check closed an hour after it ran, and we don't keep postings. Check it again."},
        )  # fmt: skip
    return _out(state)
