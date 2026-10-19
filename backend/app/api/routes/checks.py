"""The free paste check (Technical Design §11): inspect, refine, answer questions, accept patches."""

from datetime import date, datetime
from functools import cache
from typing import Annotated, Any
from zoneinfo import ZoneInfo

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.check_store import CheckState, CheckStore
from app.compliance.answers import Answers, apply_answers
from app.compliance.inspector import InputRefused, inspect
from app.compliance.llm import AnthropicLLM, LLMError, StructuredLLM
from app.compliance.models import Context, Question, Report, Verdict
from app.compliance.refiner import Patch, Refinement, finalize, refine
from app.compliance.rulepack import RulePack, load_pack
from app.core.config import settings

MAX_POSTING_CHARS = 8000

router = APIRouter(tags=["checks"])
_store = CheckStore()


def get_store() -> CheckStore:
    return _store


@cache
def _anthropic_llm(api_key: str) -> AnthropicLLM:
    return AnthropicLLM(anthropic.Anthropic(api_key=api_key))


def get_llm() -> StructuredLLM:
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="The checker isn't configured: ANTHROPIC_API_KEY is not set.")
    return _anthropic_llm(settings.ANTHROPIC_API_KEY)


@cache
def get_pack() -> RulePack:
    return load_pack("CA-ON")


def get_posting_date() -> date:
    return datetime.now(ZoneInfo("America/Toronto")).date()


StoreDep = Annotated[CheckStore, Depends(get_store)]
LLMDep = Annotated[StructuredLLM, Depends(get_llm)]
PackDep = Annotated[RulePack, Depends(get_pack)]
DateDep = Annotated[date, Depends(get_posting_date)]


class InspectIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_POSTING_CHARS)
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
    )


def _llm_failure(error: LLMError) -> HTTPException:
    return HTTPException(status_code=502, detail=f"We couldn't check this posting right now. Try again. ({error})")


def _refine(state: CheckState, pack: RulePack, llm: StructuredLLM) -> Refinement:
    return refine(
        state.inspection, state.ctx, state.posting_date, pack, llm,
        label_cache=state.label_cache, rewrites=state.rewrites,
    )  # fmt: skip


@router.post("/inspect", response_model=CheckOut)
def inspect_posting(body: InspectIn, store: StoreDep, llm: LLMDep, pack: PackDep, today: DateDep) -> Any:
    ctx = Context(meets_headcount_threshold=body.meets_headcount_threshold)
    try:
        inspection = inspect(body.text, ctx, today, pack, llm)
    except InputRefused as refused:
        raise HTTPException(status_code=422, detail={"reason": refused.reason, "message": refused.message})
    except LLMError as error:
        raise _llm_failure(error)
    return _out(store.add(CheckState(posting_date=today, ctx=ctx, inspection=inspection)))


@router.post("/refine", response_model=CheckOut)
def refine_posting(body: CheckIn, store: StoreDep, llm: LLMDep, pack: PackDep) -> Any:
    state = _state(store, body.check_id)
    try:
        state.refinement = _refine(state, pack, llm)
    except LLMError as error:
        raise _llm_failure(error)
    return _out(state)


@router.post("/answers", response_model=CheckOut)
def answer_questions(body: AnswersIn, store: StoreDep, llm: LLMDep, pack: PackDep) -> Any:
    state = _state(store, body.check_id)
    state.inspection, state.ctx = apply_answers(state.inspection, state.ctx, body.answers, pack, state.posting_date)
    if state.refinement is not None:  # answers can unlock patches (vacancy wording) or retire them
        try:
            state.refinement = _refine(state, pack, llm)
        except LLMError as error:
            raise _llm_failure(error)
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
def accept_patches(body: AcceptIn, store: StoreDep, llm: LLMDep, pack: PackDep) -> Any:
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
    return FinalOut(check_id=state.id, text=text, report=report)
