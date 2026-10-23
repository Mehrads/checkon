"""The paste check (Technical Design §11): inspect (pasted text, or a posting's link the server reads), check the
application form, refine, answer questions, accept patches, plus the research hooks (one question per result, a
custom-solution request form, feedback) and the site's contact form. Visitors get the free check's limits; a
signed-in customer on an active plan checks against the plan. The application form counts as one more check.
"""

import html
import logging
import time
import uuid
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from functools import cache
from typing import Annotated, Any, Literal, NamedTuple, Self
from zoneinfo import ZoneInfo

import anthropic
import stripe
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
)
from pydantic import BaseModel, EmailStr, Field, model_validator

from app.api.archive import purge_soon, save_applied
from app.api.billing import (
    PlanLimits,
    plan_access,
    record_final_status,
    report_extra_checks_later,
    stripe_client,
)
from app.api.check_store import CheckState, CheckStore
from app.api.deps import OptionalUserDep, SessionDep
from app.api.employer_cache import PostgresSizeCache
from app.api.free_check import (
    Limits,
    PostgresLimits,
    RateLimiter,
    client_ip,
    quota_exempt,
    rate_limited,
    refused,
    same_origin,
    visitor_cookie,
)
from app.api.posting_link import REFUSALS as LINK_REFUSALS
from app.api.posting_link import FetchedPosting, LinkReader, LinkRefused
from app.api.research import BY_ID, ResearchQuestion, question_for
from app.api.usage import PostgresUsage, Usage, elapsed_ms, visitor_hash
from app.api.workspaces import current_workspace, profile_context, wording
from app.compliance.answers import Answers, apply_answers
from app.compliance.employer import SizeCache
from app.compliance.engine import evaluate
from app.compliance.form import MAX_FORM_CHARS, classify_form, parse_form
from app.compliance.inspector import InputRefused, content_hash, inspect
from app.compliance.llm import (
    AnthropicLLM,
    LLMError,
    ModelSettings,
    SpendMeter,
    StructuredLLM,
)
from app.compliance.models import Context, Question, Report, Status, Verdict
from app.compliance.refiner import Patch, Refinement, finalize, refine
from app.compliance.rulepack import RulePack, load_pack
from app.core.config import settings
from app.models import ContactMessage, CustomRequest, Feedback, Message, ResearchAnswer

MAX_POSTING_CHARS = 8000
MAX_URL_CHARS = 2048
TORONTO = ZoneInfo("America/Toronto")

router = APIRouter(tags=["checks"], dependencies=[Depends(rate_limited), Depends(same_origin)])
_store = CheckStore()
_link_limiter = RateLimiter(settings.LINK_FETCHES_PER_HOUR, window_seconds=3600)


def get_store() -> CheckStore:
    return _store


def get_link_reader() -> LinkReader:
    return LinkReader()


def get_link_limiter() -> RateLimiter:
    return _link_limiter


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


def get_usage(session: SessionDep) -> Usage:
    return PostgresUsage(session)


def get_sizes(session: SessionDep) -> SizeCache:
    return PostgresSizeCache(session)


def get_plan_limits(session: SessionDep, user: OptionalUserDep) -> PlanLimits | None:
    """None for visitors and for signed-in users without an active plan: they get the free check."""
    access = plan_access(session, user)
    return PlanLimits(session, access) if access else None


StoreDep = Annotated[CheckStore, Depends(get_store)]
LLMDep = Annotated[StructuredLLM, Depends(get_llm)]
PackDep = Annotated[RulePack, Depends(get_pack)]
DateDep = Annotated[date, Depends(get_posting_date)]
LimitsDep = Annotated[Limits, Depends(get_limits)]
UsageDep = Annotated[Usage, Depends(get_usage)]
SizesDep = Annotated[SizeCache, Depends(get_sizes)]
PlanDep = Annotated[PlanLimits | None, Depends(get_plan_limits)]
MeterDep = Annotated[stripe.StripeClient | None, Depends(stripe_client)]
LinkReaderDep = Annotated[LinkReader, Depends(get_link_reader)]
LinkLimiterDep = Annotated[RateLimiter, Depends(get_link_limiter)]


class InspectIn(BaseModel):
    """The posting's text, or the link to its public page (which the server reads; never LinkedIn, Indeed or
    Glassdoor). Either way it is one check."""

    text: str | None = Field(default=None, min_length=1, max_length=MAX_POSTING_CHARS)
    url: str | None = Field(default=None, min_length=1, max_length=MAX_URL_CHARS)
    # Left empty by the free check, which looks the employer up. A customer's company profile fills it in.
    meets_headcount_threshold: bool | None = None
    workspace_id: uuid.UUID | None = None  # Agency: the client workspace picked in the switcher

    @model_validator(mode="after")
    def _text_or_url(self) -> Self:
        if (self.text is None) == (self.url is None):
            raise ValueError("Paste the posting's text, or give its link.")
        return self


class FormIn(BaseModel):
    check_id: str
    # One question per line, its answer options on the lines after it starting with "-"; "*" or "(required)"
    # marks a required question, "(optional)" an optional one.
    form: str = Field(min_length=1, max_length=MAX_FORM_CHARS)


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
    workspace_id: uuid.UUID | None = None  # the company profile the check started from; None for a free check
    url: str | None = None  # the page the posting was read from, for a check by link
    form_text: str | None = None  # the application form once checked; the report's form evidence points into it


class ArchiveSaved(BaseModel):
    id: uuid.UUID  # the archived posting


class FinalOut(BaseModel):
    check_id: str
    text: str  # the pasted posting with the accepted patches applied
    report: Report
    archived: ArchiveSaved | None = None  # saved to the archive: a paid check in a workspace with it on


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
        workspace_id=state.workspace_id,
        url=state.url,
        form_text=state.form,
    )


def _llm_failure(error: LLMError) -> HTTPException:
    return HTTPException(status_code=502, detail=f"We couldn't check this posting right now. Try again. ({error})")


def _spent(llm: StructuredLLM) -> Decimal:
    meter = getattr(llm, "meter", None)
    return meter.usd if meter is not None else Decimal(0)


def _charge(limits: Limits, plan: str | None, llm: StructuredLLM) -> None:
    """Free checks count toward the day's spend cap; a customer's checks don't."""
    if plan is None:
        limits.add_spend(_spent(llm))


class Visitor(NamedTuple):
    ip: str
    cookie: str
    hash: str
    exempt: bool  # our own addresses: no weekly quota, and no credit recorded


def _free_check_allowed(
    request: Request, response: Response, limits: Limits, usage: Usage, *, form: bool = False
) -> Visitor:
    ip, cookie = client_ip(request), visitor_cookie(request, response)
    visitor = Visitor(ip, cookie, visitor_hash(cookie), quota_exempt(ip))
    if not visitor.exempt and (next_check := limits.next_free_check(visitor.cookie, visitor.ip)) is not None:
        usage.record("quota", visitor=visitor.hash)  # a returning visitor, even though the check is refused
        day = next_check.astimezone(TORONTO).strftime("%B %-d")
        used = "Checking the application form uses a second check, and you've" if form else "You've"
        raise refused(429, "quota", f"{used} used this week's free check. Your next free check is available on {day}.")
    if not limits.budget_left():
        usage.record("paused", visitor=visitor.hash)
        raise refused(503, "paused", "Free checks are paused for the rest of today. Try again tomorrow.")
    return visitor


def _plan_check_allowed(plan: PlanLimits, usage: Usage) -> None:
    if (next_check := plan.next_check()) is not None:
        usage.record("quota", plan=plan.plan.id)
        day = next_check.astimezone(TORONTO).strftime("%B %-d")
        raise refused(
            429, "plan_limit",
            f"You've used this billing period's checks and {settings.PLAN_EXTRA_CHECKS_MAX} extra checks. "
            f"Checks start again on {day}. Contact us if you need more.",
        )  # fmt: skip


def _refine(state: CheckState, pack: RulePack, llm: StructuredLLM) -> Refinement:
    return refine(
        state.inspection, state.ctx, state.posting_date, pack, llm,
        variant=state.wording, label_cache=state.label_cache, rewrites=state.rewrites,
    )  # fmt: skip


def _read_link(
    url: str, request: Request, reader: LinkReader, limiter: RateLimiter, usage: Usage, who: str | None,
    plan: str | None, started: float,
) -> FetchedPosting:  # fmt: skip
    """The posting text on the page and the page's address. A link that can't be read uses no check."""

    def refuse(status: int, reason: str, message: str) -> HTTPException:
        usage.record("refused", visitor=who, status=reason, duration_ms=elapsed_ms(started), plan=plan)
        return refused(status, reason, message)

    if not limiter.allow(client_ip(request)):
        raise refuse(429, "fetch_limit", LINK_REFUSALS["fetch_limit"])
    try:
        page = reader.read(url)
    except LinkRefused as error:
        raise refuse(422, error.reason, error.message)
    if len(page.text) > MAX_POSTING_CHARS:
        raise refuse(422, "too_long", f"That page has more than {MAX_POSTING_CHARS:,} characters of text. "
                                      "Paste just the posting's text instead.")  # fmt: skip
    return page


def _link_refusal(error: InputRefused, page: FetchedPosting) -> tuple[str, str]:
    """A linked page that isn't one posting, said about the link: often a closed posting whose link now
    opens the employer's list of jobs."""
    found = "a list of jobs, not one posting" if error.reason == "multiple_postings" else "a page that isn't a job posting"
    closed = " The posting may have closed." if page.redirected else ""
    return "link_not_a_posting", (
        f"That link opens {found}.{closed} Check the link, or paste the posting's text instead."
    )


@router.post("/inspect", response_model=CheckOut)
def inspect_posting(
    body: InspectIn, request: Request, response: Response, background: BackgroundTasks, session: SessionDep,
    store: StoreDep, llm: LLMDep, pack: PackDep, today: DateDep, limits: LimitsDep, usage: UsageDep,
    sizes: SizesDep, plan: PlanDep, meter: MeterDep, reader: LinkReaderDep, link_limiter: LinkLimiterDep,
) -> Any:  # fmt: skip
    started = time.monotonic()
    paid = plan.plan.id if plan else None
    if plan is None:
        visitor: Visitor | None = _free_check_allowed(request, response, limits, usage)
    else:  # a customer's check: the plan's checks instead of the weekly limit and the spend cap
        visitor = None
        _plan_check_allowed(plan, usage)
    who = visitor.hash if visitor else None
    text, url, page = body.text or "", None, None
    if body.url is not None:  # after the quota, so a visitor with no check left can't make us fetch pages
        page = _read_link(body.url, request, reader, link_limiter, usage, who, paid, started)
        text, url = page.text, page.url
    # A customer's check starts from their company profile: its facts aren't asked or searched for.
    workspace = current_workspace(session, plan.access, body.workspace_id) if plan else None
    ctx = profile_context(workspace) if workspace else Context()
    if body.meets_headcount_threshold is not None:
        ctx = ctx.model_copy(update={"headcount": None, "meets_headcount_threshold": body.meets_headcount_threshold})
    employer = workspace.employer_name if workspace else None
    try:
        inspection = inspect(text, ctx, today, pack, llm, sizes=sizes, employer=employer)
    except InputRefused as error:  # no credit used
        reason, message = error.reason, error.message
        if page is not None and reason in ("multiple_postings", "not_a_posting"):
            reason, message = _link_refusal(error, page)
        usage.record("refused", visitor=who, status=reason, duration_ms=elapsed_ms(started), usd=_spent(llm), plan=paid)
        raise refused(422, reason, message)
    except LLMError as error:
        usage.record("failed", visitor=who, duration_ms=elapsed_ms(started), usd=_spent(llm), plan=paid)
        raise _llm_failure(error)
    finally:
        _charge(limits, paid, llm)
    if visitor and not visitor.exempt:
        limits.record_use(visitor.cookie, visitor.ip)
    state = store.add(CheckState(
        posting_date=today, ctx=inspection.context, inspection=inspection, plan=paid,
        workspace_id=workspace.id if workspace else None, wording=wording(workspace), url=url,
    ))  # fmt: skip
    if plan:
        title = inspection.facts.title.value if inspection.facts.title else None
        plan.record(state.id, title, inspection.report.status.value, state.workspace_id)
        if meter is not None:  # extra checks go to Stripe's meter after the response
            background.add_task(report_extra_checks_later, meter, plan.customer_id)
    usage.record(
        "check", check_id=state.id, visitor=who, status=inspection.report.status.value,
        duration_ms=elapsed_ms(started), usd=_spent(llm), plan=paid,
    )  # fmt: skip
    background.add_task(purge_soon)  # archived postings past their three years, whoever's check this is
    return _out(state)


FORM_REFUSALS = {
    "empty_form": "Paste the application form's questions, one per line.",
    "not_applicable": "Ontario's job posting rules don't apply to this posting, so its application form isn't checked.",
}


@router.post("/form", response_model=CheckOut)
def check_form(
    body: FormIn, request: Request, response: Response, background: BackgroundTasks, store: StoreDep,
    llm: LLMDep, pack: PackDep, limits: LimitsDep, usage: UsageDep, plan: PlanDep, meter: MeterDep,
) -> Any:  # fmt: skip
    """Check the posting's application form against the rules that cover it (ESA s. 8.3 (1)): one more check,
    on the same limits as the posting's."""
    started = time.monotonic()
    state = _state(store, body.check_id)
    if state.inspection.report.status == Status.NOT_APPLICABLE:
        raise refused(422, "not_applicable", FORM_REFUSALS["not_applicable"])
    form = parse_form(body.form)
    if not form.questions:
        raise refused(422, "empty_form", FORM_REFUSALS["empty_form"])
    paid = plan.plan.id if plan else None
    if plan is None:
        visitor: Visitor | None = _free_check_allowed(request, response, limits, usage, form=True)
    else:
        visitor = None
        _plan_check_allowed(plan, usage)
    who = visitor.hash if visitor else None
    try:
        questions = classify_form(form, pack, llm, ModelSettings())
    except LLMError as error:
        usage.record("failed", check_id=state.id, visitor=who, duration_ms=elapsed_ms(started), usd=_spent(llm), plan=paid)
        raise _llm_failure(error)
    finally:
        _charge(limits, paid, llm)
    if visitor and not visitor.exempt:
        limits.record_use(visitor.cookie, visitor.ip)

    facts = state.inspection.facts.model_copy(update={"form": questions})
    report = evaluate(facts, state.ctx, pack, state.posting_date)
    versions = {**state.inspection.report.versions, **report.versions, "form_hash": content_hash(form.text)}
    state.inspection = replace(state.inspection, facts=facts, report=report.model_copy(update={"versions": versions}))
    state.form = form.text
    if state.refinement is not None:  # its report covers the form too; rewrites come from the cache
        try:
            state.refinement = _refine(state, pack, llm)
        except LLMError as error:
            raise _llm_failure(error)
        finally:
            _charge(limits, paid, llm)

    failed = any(result.verdict == Verdict.FAIL for result in report.form_results)
    status = Status.NOT_COMPLIANT if failed else Status.COMPLIANT
    if plan:
        title = state.inspection.facts.title.value if state.inspection.facts.title else None
        plan.record(f"{state.id}-form", f"{title or 'Untitled posting'}: application form", status.value, state.workspace_id)
        if meter is not None:
            background.add_task(report_extra_checks_later, meter, plan.customer_id)
    usage.record(
        "form", check_id=state.id, visitor=who, status=status.value, duration_ms=elapsed_ms(started),
        usd=_spent(llm), count=len(questions), plan=paid,
    )  # fmt: skip
    return _out(state)


@router.post("/refine", response_model=CheckOut)
def refine_posting(
    body: CheckIn, store: StoreDep, llm: LLMDep, pack: PackDep, limits: LimitsDep, usage: UsageDep
) -> Any:
    started = time.monotonic()
    state = _state(store, body.check_id)
    try:
        state.refinement = _refine(state, pack, llm)
    except LLMError as error:
        usage.record(
            "refine", check_id=state.id, status="failed", duration_ms=elapsed_ms(started), usd=_spent(llm),
            plan=state.plan,
        )  # fmt: skip
        raise _llm_failure(error)
    finally:
        _charge(limits, state.plan, llm)
    usage.record(
        "refine", check_id=state.id, status="ok", duration_ms=elapsed_ms(started), usd=_spent(llm), plan=state.plan
    )
    return _out(state)


@router.post("/answers", response_model=CheckOut)
def answer_questions(
    body: AnswersIn, store: StoreDep, llm: LLMDep, pack: PackDep, limits: LimitsDep, usage: UsageDep
) -> Any:
    started = time.monotonic()
    state = _state(store, body.check_id)
    state.inspection, state.ctx = apply_answers(state.inspection, state.ctx, body.answers, pack, state.posting_date)
    if state.refinement is not None:  # answers can unlock patches (vacancy wording) or retire them
        try:
            state.refinement = _refine(state, pack, llm)
        except LLMError as error:
            raise _llm_failure(error)
        finally:
            _charge(limits, state.plan, llm)
    usage.record("answers", check_id=state.id, duration_ms=elapsed_ms(started), usd=_spent(llm), plan=state.plan)
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
def accept_patches(
    body: AcceptIn, session: SessionDep, store: StoreDep, llm: LLMDep, pack: PackDep, limits: LimitsDep,
    usage: UsageDep,
) -> Any:  # fmt: skip
    started = time.monotonic()
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
        _charge(limits, state.plan, llm)
    archived = None
    if state.plan:  # a free check is never archived
        record_final_status(session, state.id, report.status.value)
        archived = save_applied(session, state.id, state.workspace_id, text)
    usage.record(
        "accept", check_id=state.id, count=len(chosen), duration_ms=elapsed_ms(started), usd=_spent(llm),
        plan=state.plan,
    )  # fmt: skip
    return FinalOut(
        check_id=state.id, text=text, report=report, archived=ArchiveSaved(id=archived.id) if archived else None
    )


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
