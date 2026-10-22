"""Pay range suggestions for a paying customer's check (PRD FR9, Technical Design §9): suggest a range with its
sources, then confirm or edit it. A confirmed range is saved as that job title's band in the company profile or
client workspace the check used, and goes through the Refiner like any confirmed fact, replacing the pay
placeholder. Nothing is written into a posting until the customer confirms it. Free checks keep the placeholder.
"""

import time
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, col, select

from app.api.billing import PlanAccess, plan_access
from app.api.check_store import CheckState
from app.api.deps import CurrentUser, SessionDep
from app.api.free_check import rate_limited, same_origin
from app.api.pay_cache import PostgresPostingCache
from app.api.routes.checks import (
    TORONTO,
    CheckOut,
    DateDep,
    LimitsDep,
    LLMDep,
    PackDep,
    StoreDep,
    UsageDep,
    _charge,
    _out,
    _refine,
    _spent,
    _state,
)
from app.api.usage import elapsed_ms
from app.api.workspaces import current_workspace
from app.compliance.checks import annualise
from app.compliance.llm import SEARCH_SETTINGS, LLMError
from app.compliance.models import ExpectedPay, PayKind, PayUnit
from app.compliance.rulepack import RulePack
from app.models import Message, PayBand, Workspace, get_datetime_utc
from app.pay.jobbank import JobBank, load_job_bank
from app.pay.suggest import ConfirmedBand, PayLLM, PayRange, PostingCache, Suggestion, role_key, suggest

router = APIRouter(prefix="/pay", tags=["pay"], dependencies=[Depends(rate_limited), Depends(same_origin)])


def get_pay_access(session: SessionDep, user: CurrentUser) -> PlanAccess:
    access = plan_access(session, user)
    if access is None:
        raise HTTPException(status_code=403, detail="Pay range suggestions come with a paid plan.")
    return access


def get_postings_cache(session: SessionDep) -> PostingCache:
    return PostgresPostingCache(session)


def get_job_bank() -> JobBank:
    return load_job_bank()


AccessDep = Annotated[PlanAccess, Depends(get_pay_access)]
PostingsDep = Annotated[PostingCache, Depends(get_postings_cache)]
JobBankDep = Annotated[JobBank, Depends(get_job_bank)]
_CODE = r"^\d{5}$"


class SuggestIn(BaseModel):
    check_id: str = Field(max_length=64)
    noc_code: str | None = Field(default=None, pattern=_CODE)  # the occupation the user picked


class ConfirmIn(BaseModel):
    """The range the customer confirmed, as suggested or edited; min equal to max is a single figure."""

    check_id: str = Field(max_length=64)
    min: Decimal = Field(gt=0, le=10_000_000, decimal_places=2)
    max: Decimal = Field(gt=0, le=10_000_000, decimal_places=2)
    unit: PayUnit
    noc_code: str | None = Field(default=None, pattern=_CODE)


class BandPublic(BaseModel):
    id: uuid.UUID
    title: str
    min: Decimal
    max: Decimal
    unit: PayUnit
    noc_code: str | None
    confirmed_at: datetime


class BandsPublic(BaseModel):
    data: list[BandPublic]  # the workspace's confirmed ranges, by job title


def _paid_check(session: Session, store: Any, access: PlanAccess, check_id: str) -> tuple[CheckState, Workspace]:
    """The customer's own check on their plan, and the workspace it used. Another customer's check is refused."""
    state = _state(store, check_id)
    workspace = session.get(Workspace, state.workspace_id) if state.workspace_id else None
    if state.plan is None or workspace is None or workspace.customer_id != access.customer.id:
        raise HTTPException(status_code=403, detail="Pay range suggestions are for checks on your paid plan.")
    return state, workspace


def _title(state: CheckState) -> str:
    title = state.inspection.facts.title
    if title is None:
        raise HTTPException(status_code=422, detail="Add the job title to the posting, then check it again.")
    return title.value


def _params(pack: RulePack) -> dict[str, Any]:
    return next(rule for rule in pack.rules if rule.id == "ON-PAY-02").params


def _hours(state: CheckState, params: dict[str, Any]) -> Decimal:
    return state.ctx.hours_per_week or Decimal(params["default_hours_per_week"])


def _band(session: Session, workspace: Workspace, title: str) -> PayBand | None:
    return session.exec(
        select(PayBand).where(PayBand.workspace_id == workspace.id, PayBand.role == role_key(title))
    ).first()


@router.post("/suggest", response_model=Suggestion)
def suggest_pay(
    body: SuggestIn, session: SessionDep, access: AccessDep, store: StoreDep, llm: LLMDep, pack: PackDep,
    today: DateDep, limits: LimitsDep, usage: UsageDep, postings: PostingsDep, job_bank: JobBankDep,
) -> Any:  # fmt: skip
    """A pay range for the check's job, within the yearly cap, with the market range and each source. Asks the
    user to pick an occupation first when the posting fits two. Nothing changes in the posting."""
    started = time.monotonic()
    state, workspace = _paid_check(session, store, access, body.check_id)
    title = _title(state)
    if (known := state.pay_suggestions.get(body.noc_code or "")) is not None:  # asked again: no new spend
        return known
    params = _params(pack)
    row = _band(session, workspace, title)
    band = ConfirmedBand(
        title=row.title, range=PayRange(min=row.min, max=row.max, unit=PayUnit(row.unit)),
        confirmed_on=row.confirmed_at.astimezone(TORONTO).date(),
    ) if row else None  # fmt: skip
    facts = state.inspection.facts
    wages = [pay for pay in facts.pay if pay.kind == PayKind.WAGE]
    try:
        suggestion = suggest(
            title=title, location=facts.locations[0].value if facts.locations else None,
            posting=state.inspection.document.text, hours=_hours(state, params), params=params, band=band,
            unit_hint=wages[0].unit if wages else None, noc=body.noc_code, job_bank=job_bank,
            llm=cast(PayLLM, llm), today=today, search_settings=SEARCH_SETTINGS, postings_cache=postings,
        )  # fmt: skip
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    except LLMError as error:
        usage.record(
            "pay_suggest", check_id=state.id, status="failed", duration_ms=elapsed_ms(started), usd=_spent(llm),
            plan=state.plan,
        )  # fmt: skip
        raise HTTPException(status_code=502, detail=f"We couldn't suggest pay right now. Try again. ({error})")
    finally:
        limits.add_spend(_spent(llm))  # the day's spend meter: free checks and pay suggestions
    state.pay_suggestions[body.noc_code or ""] = suggestion
    usage.record(
        "pay_suggest", check_id=state.id, status=suggestion.status, duration_ms=elapsed_ms(started),
        usd=_spent(llm), plan=state.plan,
    )  # fmt: skip
    return suggestion


@router.post("/confirm", response_model=CheckOut)
def confirm_pay(
    body: ConfirmIn, session: SessionDep, access: AccessDep, store: StoreDep, llm: LLMDep, pack: PackDep,
    limits: LimitsDep, usage: UsageDep,
) -> Any:  # fmt: skip
    """Save the confirmed range as the job title's band in the check's workspace, and refine the posting with it:
    it replaces the pay placeholder, or a range that is too wide or open-ended."""
    started = time.monotonic()
    state, workspace = _paid_check(session, store, access, body.check_id)
    title = _title(state)
    params = _params(pack)
    if body.min > body.max:
        raise HTTPException(status_code=422, detail="The lowest pay can't be more than the highest.")
    hours = _hours(state, params)
    width = annualise(body.max - body.min, body.unit, hours, params)
    exempt = annualise(body.max, body.unit, hours, params) > params["exemption_threshold_annual"]
    if width > params["max_annual_width"] and not exempt:
        raise HTTPException(
            status_code=422,
            detail=f"That range is ${width:,.0f} a year wide. Keep it within ${params['max_annual_width']:,.0f} a year.",
        )
    values = {
        "min": body.min, "max": body.max, "unit": body.unit.value, "title": title[:255], "noc_code": body.noc_code,
        "confirmed_at": get_datetime_utc(), "confirmed_by": access.user.id,
    }  # fmt: skip
    session.exec(
        insert(PayBand)
        .values(id=uuid.uuid4(), workspace_id=workspace.id, role=role_key(title), **values)
        .on_conflict_do_update(index_elements=["workspace_id", "role"], set_=values)
    )  # fmt: skip
    session.commit()
    state.pay_suggestions.clear()  # the band changed
    state.ctx = state.ctx.model_copy(update={"expected_pay": ExpectedPay(min=body.min, max=body.max, unit=body.unit)})
    try:
        state.refinement = _refine(state, pack, llm)
    except LLMError as error:
        raise HTTPException(status_code=502, detail=f"We couldn't update the fixes right now. Try again. ({error})")
    finally:
        _charge(limits, state.plan, llm)
    usage.record(
        "pay_confirm", check_id=state.id, status="ok", duration_ms=elapsed_ms(started), usd=_spent(llm),
        plan=state.plan,
    )  # fmt: skip
    return _out(state)


@router.get("/bands", response_model=BandsPublic)
def read_bands(session: SessionDep, access: AccessDep, workspace_id: uuid.UUID | None = None) -> Any:
    """The pay ranges confirmed in the current workspace (Agency: the one asked for), by job title."""
    workspace = current_workspace(session, access, workspace_id)
    rows = session.exec(
        select(PayBand).where(PayBand.workspace_id == workspace.id).order_by(col(PayBand.title))
    ).all()
    return BandsPublic(data=[BandPublic.model_validate(row, from_attributes=True) for row in rows])


@router.delete("/bands/{band_id}", response_model=Message)
def delete_band(band_id: uuid.UUID, session: SessionDep, access: AccessDep) -> Any:
    band = session.get(PayBand, band_id)
    workspace = session.get(Workspace, band.workspace_id) if band else None
    if band is None or workspace is None or workspace.customer_id != access.customer.id:
        raise HTTPException(status_code=404, detail="Pay range not found.")
    session.delete(band)
    session.commit()
    return Message(message="Pay range removed.")
