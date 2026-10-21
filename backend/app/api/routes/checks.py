"""The free paste check (Technical Design §11): inspect, refine, answer questions, accept patches,
plus the research hooks (one question per result, a custom-solution request form, feedback)
and the site's contact form.
"""

from datetime import date, datetime
from decimal import Decimal
from functools import cache
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo

import html
import logging

import anthropic
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

from app.api.check_store import CheckState, CheckStore
from app.api.deps import SessionDep
from app.api.free_check import (
    Limits,
    PostgresLimits,
    client_ip,
    rate_limited,
    refused,
    same_origin,
    visitor_cookie,
)
from app.api.research import BY_ID, ResearchQuestion, question_for
from app.compliance.answers import Answers, apply_answers
from app.compliance.inspector import InputRefused, inspect
from app.compliance.llm import AnthropicLLM, LLMError, SpendMeter, StructuredLLM
from app.compliance.models import Context, Question, Report, Verdict
from app.compliance.refiner import Patch, Refinement, finalize, refine
from app.compliance.rulepack import RulePack, load_pack
from app.core.config import settings
from app.models import ContactMessage, CustomRequest, Feedback, Message, ResearchAnswer

MAX_POSTING_CHARS = 8000
TORONTO = ZoneInfo("America/Toronto")

router = APIRouter(tags=["checks"], dependencies=[Depends(rate_limited), Depends(same_origin)])
_store = CheckStore()


def get_store() -> CheckStore:
    return _store


@cache
def _anthropic_client(api_key: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key)


def get_llm() -> StructuredLLM:
    """A fresh wrapper per request, so its meter counts only this request's spend."""
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="The checker isn't configured: ANTHROPIC_API_KEY is not set.")
    return AnthropicLLM(_anthropic_client(settings.ANTHROPIC_API_KEY), meter=SpendMeter())


@cache
def get_pack() -> RulePack:
    return load_pack("CA-ON")


def get_posting_date() -> date:
    return datetime.now(TORONTO).date()


def get_limits(session: SessionDep, today: Annotated[date, Depends(get_posting_date)]) -> Limits:
    return PostgresLimits(
        session, today, settings.FREE_CHECKS_PER_WEEK, settings.FREE_CHECK_DAILY_SPEND_CAP_USD, settings.SECRET_KEY
    )


StoreDep = Annotated[CheckStore, Depends(get_store)]
LLMDep = Annotated[StructuredLLM, Depends(get_llm)]
PackDep = Annotated[RulePack, Depends(get_pack)]
DateDep = Annotated[date, Depends(get_posting_date)]
LimitsDep = Annotated[Limits, Depends(get_limits)]


class InspectIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_POSTING_CHARS)
    # Left empty by the free check, which looks the employer up; set it when the profile knows.
    meets_headcount_threshold: bool | None = None


class CheckIn(BaseModel):
    check_id: str


class AnswersIn(BaseModel):
    check_id: str
    answers: Answers


class Decision(BaseModel):
    patch_id: str
    accept: bool
    option: int | None = None  # index into the patch's options, for a patch that offers a choice


class AcceptIn(BaseModel):
    check_id: str
    decisions: list[Decision] = []


class CheckOut(BaseModel):
    check_id: str
    text: str  # the normalised posting; every span in the report and patches points into it
    report: Report
    refinement: Refinement | None = None
    questions: list[Question]  # open questions, from the report and the refinement
    research_question: ResearchQuestion  # one optional market-research question per check


class FinalOut(BaseModel):
    check_id: str
    text: str  # the pasted posting with the accepted patches applied
    report: Report


def _state(store: CheckStore, check_id: str) -> CheckState:
    state = store.get(check_id)
    if state is None:
        raise HTTPException(status_code=404, detail="This check has expired. Paste the posting again.")
    return state


def _out(state: CheckState) -> CheckOut:
    questions: dict[str, Question] = {}
    for result in state.inspection.report.results:
        if result.verdict == Verdict.NEEDS_INPUT and result.question and result.question.kind != "none":
            questions.setdefault(result.question.id, result.question)
    for question in state.refinement.questions if state.refinement else []:
        questions.setdefault(question.id, question)
    return CheckOut(
        check_id=state.id,
        text=state.inspection.document.text,
        report=state.inspection.report,
        refinement=state.refinement,
        questions=list(questions.values()),
        research_question=question_for(state.id),
    )


def _llm_failure(error: LLMError) -> HTTPException:
    return HTTPException(status_code=502, detail=f"We couldn't check this posting right now. Try again. ({error})")


def _spent(llm: StructuredLLM) -> Decimal:
    meter = getattr(llm, "meter", None)
    return meter.usd if meter is not None else Decimal(0)


def _refine(state: CheckState, pack: RulePack, llm: StructuredLLM) -> Refinement:
    return refine(
        state.inspection, state.ctx, state.posting_date, pack, llm,
        label_cache=state.label_cache, rewrites=state.rewrites,
    )  # fmt: skip


@router.post("/inspect", response_model=CheckOut)
def inspect_posting(
    body: InspectIn, request: Request, response: Response, store: StoreDep, llm: LLMDep, pack: PackDep,
    today: DateDep, limits: LimitsDep,
) -> Any:  # fmt: skip
    ip, cookie = client_ip(request), visitor_cookie(request, response)
    if (next_check := limits.next_free_check(cookie, ip)) is not None:
        day = next_check.astimezone(TORONTO).strftime("%B %-d")
        raise refused(429, "quota", f"You've used this week's free check. Your next free check is available on {day}.")
    if not limits.budget_left():
        raise refused(503, "paused", "Free checks are paused for the rest of today. Try again tomorrow.")
    ctx = Context(meets_headcount_threshold=body.meets_headcount_threshold)
    try:
        inspection = inspect(body.text, ctx, today, pack, llm)
    except InputRefused as error:  # no credit used
        raise refused(422, error.reason, error.message)
    except LLMError as error:
        raise _llm_failure(error)
    finally:
        limits.add_spend(_spent(llm))
    limits.record_use(cookie, ip)
    return _out(store.add(CheckState(posting_date=today, ctx=inspection.context, inspection=inspection)))


@router.post("/refine", response_model=CheckOut)
def refine_posting(body: CheckIn, store: StoreDep, llm: LLMDep, pack: PackDep, limits: LimitsDep) -> Any:
    state = _state(store, body.check_id)
    try:
        state.refinement = _refine(state, pack, llm)
    except LLMError as error:
        raise _llm_failure(error)
    finally:
        limits.add_spend(_spent(llm))
    return _out(state)


@router.post("/answers", response_model=CheckOut)
def answer_questions(body: AnswersIn, store: StoreDep, llm: LLMDep, pack: PackDep, limits: LimitsDep) -> Any:
    state = _state(store, body.check_id)
    state.inspection, state.ctx = apply_answers(state.inspection, state.ctx, body.answers, pack, state.posting_date)
    if state.refinement is not None:  # answers can unlock patches (vacancy wording) or retire them
        try:
            state.refinement = _refine(state, pack, llm)
        except LLMError as error:
            raise _llm_failure(error)
        finally:
            limits.add_spend(_spent(llm))
    return _out(state)


def _chosen(refinement: Refinement, decisions: list[Decision]) -> list[Patch]:
    by_id = {d.patch_id: d for d in decisions}
    unknown = set(by_id) - {p.id for p in refinement.patches}
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown patches: {', '.join(sorted(unknown))}")
    chosen = []
    for patch in refinement.patches:
        decision = by_id.get(patch.id)
        if not (decision.accept if decision else patch.default):
            continue
        if patch.options:
            if decision is None or decision.option is None or not 0 <= decision.option < len(patch.options):
                raise HTTPException(status_code=422, detail=f"Pick one of the options for {patch.id}.")
            patch = patch.model_copy(update={"after": patch.options[decision.option]})
        if patch.after is not None:
            chosen.append(patch)
    return chosen


@router.post("/patches/accept", response_model=FinalOut)
def accept_patches(body: AcceptIn, store: StoreDep, llm: LLMDep, pack: PackDep, limits: LimitsDep) -> Any:
    state = _state(store, body.check_id)
    if state.refinement is None:
        raise HTTPException(status_code=409, detail="Refine the posting before accepting patches.")
    chosen = _chosen(state.refinement, body.decisions)
    try:
        text, report = finalize(
            state.inspection, state.ctx, state.posting_date, pack, llm, chosen, label_cache=state.label_cache
        )
    except LLMError as error:
        raise _llm_failure(error)
    finally:
        limits.add_spend(_spent(llm))
    return FinalOut(check_id=state.id, text=text, report=report)


# Research hooks


class ResearchAnswerIn(BaseModel):
    check_id: str = Field(max_length=64)
    question_id: str = Field(max_length=64)
    answer: str = Field(max_length=255)


class CustomRequestIn(BaseModel):
    check_id: str | None = Field(default=None, max_length=64)
    hr_system: str = Field(min_length=1, max_length=255)
    postings_per_month: str = Field(min_length=1, max_length=64)
    wants: str = Field(min_length=1, max_length=2000)
    email: EmailStr = Field(max_length=255)


class FeedbackIn(BaseModel):
    check_id: str = Field(max_length=64)
    target_kind: Literal["finding", "patch", "check"]
    target_id: str = Field(max_length=64)
    rating: Literal["up", "down", "looks_wrong"]
    reason: Literal["wrong_rule", "missed_issue", "bad_wording", "other"] | None = None
    comment: str | None = Field(default=None, max_length=2000)
    share_posting: bool = False  # consent to keep the posting text for review


@router.post("/research/answer", status_code=201)
def answer_research(body: ResearchAnswerIn, session: SessionDep) -> Message:
    question = BY_ID.get(body.question_id)
    if question is None or body.answer not in question.options:
        raise HTTPException(status_code=422, detail="Unknown question or answer.")
    session.add(ResearchAnswer(check_id=body.check_id, question_id=body.question_id, answer=body.answer))
    session.commit()
    return Message(message="Thanks!")


@router.post("/requests", status_code=201)
def request_custom_solution(body: CustomRequestIn, session: SessionDep) -> Message:
    session.add(CustomRequest(**body.model_dump()))
    session.commit()
    return Message(message="Thanks! We'll email you about your request.")


@router.post("/feedback", status_code=201)
def send_feedback(body: FeedbackIn, session: SessionDep, store: StoreDep) -> Message:
    state = store.get(body.check_id)
    versions = state.inspection.report.versions if state else {}
    posting = state.inspection.document.original if state and body.share_posting else None
    session.add(Feedback(**body.model_dump(exclude={"share_posting"}), versions=versions, posting_text=posting))
    session.commit()
    return Message(message="Thanks for the feedback.")


# Contact form

logger = logging.getLogger(__name__)

INTERESTS = {"starter": "Starter plan", "agency": "Agency plan", "custom": "Custom setup", "other": "Something else"}


class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr = Field(max_length=255)
    company: str | None = Field(default=None, max_length=255)
    interest: Literal["starter", "agency", "custom", "other"]
    message: str = Field(min_length=1, max_length=2000)
    check_id: str | None = Field(default=None, max_length=64)


def _notify(contact: ContactMessage) -> None:
    from app.utils import send_email  # the template's SMTP helper

    rows = [("From", f"{contact.name} <{contact.email}>"), ("Company", contact.company or "-"),
            ("Interested in", INTERESTS[contact.interest]), ("Message", contact.message)]  # fmt: skip
    body = "".join(f"<p><strong>{label}:</strong> {html.escape(value)}</p>" for label, value in rows)
    try:
        send_email(
            email_to=str(settings.CONTACT_EMAIL),
            subject=f"CheckON: {INTERESTS[contact.interest]} enquiry from {contact.name}",
            html_content=body.replace("\n", "<br>"),
        )
    except Exception:  # the message is saved either way
        logger.exception("Could not email contact message %s", contact.id)


@router.post("/contact", status_code=201)
def contact(body: ContactIn, session: SessionDep, background: BackgroundTasks) -> Message:
    message = ContactMessage(**body.model_dump())
    session.add(message)
    session.commit()
    session.refresh(message)
    if settings.CONTACT_EMAIL and settings.emails_enabled:
        background.add_task(_notify, message)
    return Message(message="Thanks! We'll get back to you by email.")
