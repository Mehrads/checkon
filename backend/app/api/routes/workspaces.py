"""The company profile a paying customer's checks start from (PRD FR2)."""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.billing import PlanAccess, plan_access
from app.api.deps import CurrentUser, SessionDep
from app.api.routes.checks import get_pack
from app.api.workspaces import Wording, current_workspace
from app.models import Workspace, get_datetime_utc

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def get_plan_access(session: SessionDep, user: CurrentUser) -> PlanAccess:
    access = plan_access(session, user)
    if access is None:
        raise HTTPException(status_code=403, detail="A company profile comes with a paid plan.")
    return access


PlanAccessDep = Annotated[PlanAccess, Depends(get_plan_access)]


class WorkspacePublic(BaseModel):
    id: uuid.UUID
    employer_name: str | None
    headcount: int | None
    meets_headcount_threshold: bool | None
    uses_ai_in_hiring: bool | None
    wording: Wording
    updated_at: datetime | None
    headcount_threshold: int  # the rule pack's employer size, for the profile form's wording


class ProfileUpdate(BaseModel):
    """Only the fields sent are changed. A headcount replaces "25 or more", and the other way round."""

    model_config = ConfigDict(extra="forbid")
    employer_name: str | None = Field(default=None, max_length=255)
    headcount: int | None = Field(default=None, ge=0, le=10_000_000)
    meets_headcount_threshold: bool | None = None
    uses_ai_in_hiring: bool | None = None
    wording: Wording = "formal"

    @field_validator("employer_name")
    @classmethod
    def _blank_is_none(cls, value: str | None) -> str | None:
        return " ".join(value.split()) or None if value is not None else None


def _public(workspace: Workspace) -> WorkspacePublic:
    rule = next(r for r in get_pack().rules if r.id == "ON-APPL-01")
    threshold = rule.params["min_employees"]
    return WorkspacePublic.model_validate({**workspace.model_dump(), "headcount_threshold": threshold})


def _mine(session: SessionDep, access: PlanAccess, workspace_id: uuid.UUID) -> Workspace:
    workspace = session.get(Workspace, workspace_id)
    if workspace is None or workspace.customer_id != access.customer.id:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    return workspace


@router.get("/current", response_model=WorkspacePublic)
def read_current_workspace(session: SessionDep, access: PlanAccessDep) -> Any:
    """The company profile the customer's checks use."""
    return _public(current_workspace(session, access.customer))


@router.patch("/{workspace_id}", response_model=WorkspacePublic)
def update_workspace(
    workspace_id: uuid.UUID, body: ProfileUpdate, session: SessionDep, access: PlanAccessDep
) -> Any:
    """Change the company profile: the fields sent, such as one answer saved during a check."""
    workspace = _mine(session, access, workspace_id)
    update = body.model_dump(exclude_unset=True)
    if update.get("headcount") is not None:
        update["meets_headcount_threshold"] = None
    if update.get("meets_headcount_threshold") is not None:
        update["headcount"] = None
    workspace.sqlmodel_update(update)
    workspace.updated_at = get_datetime_utc()
    session.add(workspace)
    session.commit()
    session.refresh(workspace)
    return _public(workspace)
