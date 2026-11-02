"""Outreach reports: a careers page audit we ran before the company asked for anything, saved by the outreach
workflow (.claude/workflows/prospect-outreach.js) with OUTREACH_API_KEY, after a second agent confirmed every
finding. The pitch email links to the report's private page, which opens without signing in: each open Ontario
posting, what it may miss with its own words quoted, its application form's findings, and the hiring-process
questions no posting shows (the 45-day reply, the 3-year records). From there the company signs up for a free
account and the report is saved to it, then fixes each posting with a check. We see every report, its views and
whether it was saved on the admin's Outreach page.

A report nobody saves is deleted REPORT_DAYS after it was made. It never holds a posting's whole text or anyone's
contact details: those stay in the workflow's own folder.
"""

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session, col, delete, select

from app.api.deps import (
    CurrentUser,
    OptionalUserDep,
    SessionDep,
    get_current_active_superuser,
)
from app.api.free_check import rate_limited, same_origin
from app.api.routes.checks import get_pack
from app.core.config import settings
from app.models import Customer, OutreachPosting, OutreachReport, User, get_datetime_utc

router = APIRouter(tags=["reports"])

# The hiring-process rules a posting can't show: the report asks about them instead
PROCESS_RULES = ("ON-INT-01", "ON-REC-01")
Answer = Literal["yes", "no", "unsure"]
FindingVerdict = Literal["fail", "warning", "needs_input"]
PostingStatus = Literal["compliant", "not_compliant", "needs_input", "not_applicable", "refused", "failed"]
FormStatus = Literal["compliant", "not_compliant"]


def outreach_key(authorization: Annotated[str | None, Header()] = None) -> None:
    """Saving a report takes the outreach workflow's key, sent as a bearer token."""
    if not settings.OUTREACH_API_KEY:
        raise HTTPException(status_code=503, detail="Outreach reports aren't set up: OUTREACH_API_KEY is not set.")
    sent = (authorization or "").removeprefix("Bearer ").strip()
    if not secrets.compare_digest(sent.encode(), settings.OUTREACH_API_KEY.encode()):
        raise HTTPException(status_code=401, detail="Wrong outreach key.")


# The shapes


class ReportFinding(BaseModel):
    rule: str = Field(max_length=32)
    verdict: FindingVerdict
    message: str = Field(max_length=500)
    quotes: list[Annotated[str, Field(max_length=300)]] = Field(default=[], max_length=5)  # the posting's words

    @field_validator("rule")
    @classmethod
    def _known_rule(cls, rule: str) -> str:
        if rule not in {r.id for r in get_pack().rules}:
            raise ValueError(f"{rule} isn't a rule in the rule pack")
        return rule


class PostingIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    url: str = Field(max_length=2048, pattern=r"^https?://")
    where: Literal["ontario", "canada"]
    status: PostingStatus
    findings: list[ReportFinding] = Field(default=[], max_length=12)
    form_status: FormStatus | None = None  # None: the form couldn't be read
    form_findings: list[ReportFinding] = Field(default=[], max_length=12)
    note: str | None = Field(default=None, max_length=255)


class ReportIn(BaseModel):
    company: str = Field(min_length=1, max_length=255)
    url: str = Field(max_length=2048, pattern=r"^https?://")
    found: int = Field(ge=0)
    outside_ontario: int = Field(ge=0)
    postings: list[PostingIn] = Field(max_length=100)


class ReportCreated(BaseModel):
    id: uuid.UUID
    token: str
    link: str  # the private page to put in the email


class PostingOut(BaseModel):
    title: str
    location: str | None
    url: str
    where: str
    status: str
    findings: list[ReportFinding]
    form_status: str | None
    form_findings: list[ReportFinding]
    note: str | None


class ReportOut(BaseModel):
    token: str
    company: str
    url: str
    created_at: datetime
    found: int
    outside_ontario: int
    postings: list[PostingOut]
    checklist: dict[str, Answer]
    saved: bool  # to some account
    mine: bool  # to the signed-in user's account
    expires_on: datetime | None  # when it's deleted unless someone saves it


class ReportSummary(BaseModel):
    token: str
    company: str
    url: str
    created_at: datetime
    postings: int
    to_fix: int  # postings that may need changes: the report page's tile and the outreach note count the same
    saved_at: datetime | None


class OutreachSummary(ReportSummary):
    views: int
    first_viewed_at: datetime | None
    saved_by: str | None  # the account's email


class ChecklistIn(BaseModel):
    answers: dict[str, Answer]

    @field_validator("answers")
    @classmethod
    def _process_rules(cls, answers: dict[str, Answer]) -> dict[str, Answer]:
        if unknown := set(answers) - set(PROCESS_RULES):
            raise ValueError(f"Not a hiring-process question: {', '.join(sorted(unknown))}")
        return answers


# Helpers


def _expires(report: OutreachReport) -> datetime | None:
    return None if report.customer_id else report.created_at + timedelta(days=settings.REPORT_DAYS)


def purge_reports(session: Session, now: datetime) -> int:
    """Delete the reports nobody saved within REPORT_DAYS; their postings go with them."""
    result = session.exec(
        delete(OutreachReport).where(
            col(OutreachReport.customer_id).is_(None),
            col(OutreachReport.created_at) < now - timedelta(days=settings.REPORT_DAYS),
        )
    )
    session.commit()
    return result.rowcount  # type: ignore[attr-defined]


def _report(session: Session, token: str) -> OutreachReport:
    report = session.exec(select(OutreachReport).where(OutreachReport.token == token)).first()
    expires = _expires(report) if report else None
    if report is None or (expires is not None and expires <= get_datetime_utc()):
        raise HTTPException(status_code=404, detail="This report doesn't exist or has expired.")
    return report


def _postings(session: Session, report_id: uuid.UUID) -> list[OutreachPosting]:
    return list(
        session.exec(
            select(OutreachPosting)
            .where(OutreachPosting.report_id == report_id)
            .order_by(col(OutreachPosting.position))
        ).all()
    )


def _to_fix(postings: list[OutreachPosting]) -> int:
    """Postings with a fail or warning, or a form that isn't compliant: a needs_input finding only asks a question."""
    return sum(
        1 for p in postings
        if any(f["verdict"] in ("fail", "warning") for f in p.findings + p.form_findings)
        or p.form_status == "not_compliant"
    )  # fmt: skip


def _out(session: Session, report: OutreachReport, user: User | None) -> ReportOut:
    postings = _postings(session, report.id)
    return ReportOut(
        token=report.token, company=report.company, url=report.url, created_at=report.created_at,
        found=report.found, outside_ontario=report.outside_ontario,
        postings=[PostingOut.model_validate(p, from_attributes=True) for p in postings],
        checklist=report.checklist or {}, saved=report.customer_id is not None,
        mine=bool(user and user.customer_id and user.customer_id == report.customer_id),
        expires_on=_expires(report),
    )  # fmt: skip


def _summary(session: Session, report: OutreachReport) -> dict[str, Any]:
    postings = _postings(session, report.id)
    return {
        "token": report.token, "company": report.company, "url": report.url, "created_at": report.created_at,
        "postings": len(postings), "to_fix": _to_fix(postings), "saved_at": report.saved_at,
    }  # fmt: skip


# Saved by the outreach workflow


@router.post("/outreach/reports", response_model=ReportCreated, dependencies=[Depends(outreach_key)])
def create_report(body: ReportIn, session: SessionDep) -> Any:
    """Save a report the outreach workflow made, and give its private link."""
    purge_reports(session, get_datetime_utc())
    report = OutreachReport(
        token=secrets.token_urlsafe(24), company=body.company.strip(), url=body.url, found=body.found,
        outside_ontario=body.outside_ontario,
    )  # fmt: skip
    session.add(report)
    session.flush()
    for position, posting in enumerate(body.postings):
        session.add(OutreachPosting(report_id=report.id, position=position, **posting.model_dump()))
    session.commit()
    return ReportCreated(id=report.id, token=report.token, link=f"{settings.FRONTEND_HOST}/report/{report.token}")


@router.get(
    "/outreach/reports", response_model=list[OutreachSummary], dependencies=[Depends(get_current_active_superuser)]
)
def read_outreach_reports(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """Every outreach report, newest first: who opened it, and who saved it."""
    rows = session.exec(
        select(OutreachReport, Customer)
        .join(Customer, col(OutreachReport.customer_id) == Customer.id, isouter=True)
        .order_by(col(OutreachReport.created_at).desc())
        .offset(skip)
        .limit(min(limit, 200))
    ).all()
    return [
        OutreachSummary(
            **_summary(session, report), views=report.views, first_viewed_at=report.first_viewed_at,
            saved_by=customer.email if customer else None,
        )  # fmt: skip
        for report, customer in rows
    ]


# The company's side


@router.get("/reports/{token}", response_model=ReportOut)
def read_report(token: str, session: SessionDep, user: OptionalUserDep) -> Any:
    """The report, for anyone with its link. A view by one of us isn't counted."""
    report = _report(session, token)
    if not (user and user.is_superuser):
        report.views += 1
        report.first_viewed_at = report.first_viewed_at or get_datetime_utc()
        session.add(report)
        session.commit()
        session.refresh(report)
    return _out(session, report, user)


@router.put(
    "/reports/{token}/checklist", response_model=ReportOut, dependencies=[Depends(rate_limited), Depends(same_origin)]
)
def answer_checklist(token: str, body: ChecklistIn, session: SessionDep, user: OptionalUserDep) -> Any:
    """Answers to the hiring-process questions, kept with the report."""
    report = _report(session, token)
    report.checklist = {**(report.checklist or {}), **body.answers}
    session.add(report)
    session.commit()
    session.refresh(report)
    return _out(session, report, user)


@router.post("/reports/{token}/save", response_model=ReportOut, dependencies=[Depends(same_origin)])
def save_report(token: str, session: SessionDep, user: CurrentUser) -> Any:
    """Save the report to the signed-in user's account: free or paid, it then lists it."""
    report = _report(session, token)
    if user.customer_id is None:
        raise HTTPException(status_code=409, detail="Reports are saved to a CheckON account. Sign up for a free one.")
    if report.customer_id not in (None, user.customer_id):
        raise HTTPException(status_code=409, detail="This report is already saved to another CheckON account.")
    if report.customer_id is None:
        report.customer_id, report.saved_at = user.customer_id, get_datetime_utc()
        session.add(report)
        session.commit()
        session.refresh(report)
    return _out(session, report, user)


@router.get("/reports", response_model=list[ReportSummary])
def read_my_reports(session: SessionDep, user: CurrentUser) -> Any:
    """The reports saved to the user's account, newest first."""
    if user.customer_id is None:
        return []
    reports = session.exec(
        select(OutreachReport)
        .where(OutreachReport.customer_id == user.customer_id)
        .order_by(col(OutreachReport.created_at).desc())
    ).all()
    return [ReportSummary(**_summary(session, report)) for report in reports]
