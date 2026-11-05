"""The company profiles a signed-in account's checks start from, one per client workspace: list, create, rename,
archive, and pick the one checks use.
"""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlmodel import col, func, select

from app.api.accounts import Access, access_for
from app.api.deps import CurrentUser, SessionDep
from app.api.routes.checks import get_pack
from app.api.workspaces import (
    MAX_WORKSPACES,
    Wording,
    current_workspace,
    label,
    open_workspaces,
)
from app.models import Workspace, get_datetime_utc

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def get_access(session: SessionDep, user: CurrentUser) -> Access:
    access = access_for(session, user)
    assert access is not None  # CurrentUser is signed in
    return access


AccessDep = Annotated[Access, Depends(get_access)]


def _clean(value: Any) -> Any:
    """Spaces collapsed; a blank name is no name."""
    return " ".join(value.split()) or None if isinstance(value, str) else value


class WorkspacePublic(BaseModel):
    id: uuid.UUID
    name: str  # the client's name, else the employer's, else "Your company"
    employer_name: str | None
    headcount: int | None
    meets_headcount_threshold: bool | None
    uses_ai_in_hiring: bool | None
    wording: Wording
    archive_postings: bool  # the archive is on: each check's applied posting is kept
    updated_at: datetime | None
    headcount_threshold: int  # the rule pack's employer size, for the profile form's wording


class WorkspacesPublic(BaseModel):
    data: list[WorkspacePublic]  # open workspaces, oldest first
    current_id: uuid.UUID  # the one checks use
    can_create: bool  # under the limit of open workspaces


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)

    @field_validator("name", mode="before")
    @classmethod
    def _name(cls, value: Any) -> Any:
        return _clean(value) or ""


class WorkspaceUpdate(BaseModel):
    """Only the fields sent are changed. A headcount replaces "25 or more", and the other way round."""

    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, max_length=255)
    employer_name: str | None = Field(default=None, max_length=255)
    headcount: int | None = Field(default=None, ge=0, le=10_000_000)
    meets_headcount_threshold: bool | None = None
    uses_ai_in_hiring: bool | None = None
    wording: Wording = "formal"
    archive_postings: bool = False

    @field_validator("name", "employer_name", mode="before")
    @classmethod
    def _names(cls, value: Any) -> Any:
        return _clean(value)


class CurrentIn(BaseModel):
    workspace_id: uuid.UUID


def _public(workspace: Workspace) -> WorkspacePublic:
    rule = next(r for r in get_pack().rules if r.id == "ON-APPL-01")
    threshold = rule.params["min_employees"]
    return WorkspacePublic.model_validate(
        {**workspace.model_dump(), "name": label(workspace), "headcount_threshold": threshold}
    )


def _mine(session: SessionDep, access: Access, workspace_id: uuid.UUID) -> Workspace:
    workspace = session.get(Workspace, workspace_id)
    if workspace is None or workspace.customer_id != access.customer.id or workspace.archived_at is not None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    return workspace


@router.get("/", response_model=WorkspacesPublic)
def read_workspaces(session: SessionDep, access: AccessDep) -> Any:
    """The customer's open workspaces and the one checks use. Starter has exactly one."""
    current = current_workspace(session, access)
    workspaces = open_workspaces(session, access.customer)
    return WorkspacesPublic(
        data=[_public(w) for w in workspaces], current_id=current.id, can_create=len(workspaces) < MAX_WORKSPACES
    )


@router.post("/", response_model=WorkspacePublic, status_code=201)
def create_workspace(body: WorkspaceCreate, session: SessionDep, access: AccessDep) -> Any:
    """A workspace for a new client, with an empty company profile. Checks use it from now on."""
    opened = session.exec(
        select(func.count()).select_from(Workspace).where(
            Workspace.customer_id == access.customer.id, col(Workspace.archived_at).is_(None)
        )
    ).one()  # fmt: skip
    if opened >= MAX_WORKSPACES:
        raise HTTPException(status_code=409, detail=f"You can have {MAX_WORKSPACES} open workspaces. Archive one first.")
    workspace = Workspace(customer_id=access.customer.id, name=body.name)
    session.add(workspace)
    session.flush()
    access.user.workspace_id = workspace.id
    session.add(access.user)
    session.commit()
    session.refresh(workspace)
    return _public(workspace)


@router.get("/current", response_model=WorkspacePublic)
def read_current_workspace(session: SessionDep, access: AccessDep) -> Any:
    """The company profile the customer's checks use."""
    return _public(current_workspace(session, access))


@router.put("/current", response_model=WorkspacePublic)
def switch_workspace(body: CurrentIn, session: SessionDep, access: AccessDep) -> Any:
    """Pick the client workspace checks use, on the website and in the extension."""
    workspace = _mine(session, access, body.workspace_id)
    access.user.workspace_id = workspace.id
    session.add(access.user)
    session.commit()
    session.refresh(workspace)
    return _public(workspace)


@router.patch("/{workspace_id}", response_model=WorkspacePublic)
def update_workspace(
    workspace_id: uuid.UUID, body: WorkspaceUpdate, session: SessionDep, access: AccessDep
) -> Any:
    """Rename a workspace or change its company profile: the fields sent, such as one answer saved during a
    check."""
    workspace = _mine(session, access, workspace_id)
    update = body.model_dump(exclude_unset=True)
    if "name" in update and update["name"] is None:
        raise HTTPException(status_code=422, detail="Give the workspace a name.")
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


@router.post("/{workspace_id}/archive", response_model=WorkspacesPublic)
def archive_workspace(workspace_id: uuid.UUID, session: SessionDep, access: AccessDep) -> Any:
    """Hide a client's workspace from the switcher and stop using its profile. Its past checks keep its name."""
    workspace = _mine(session, access, workspace_id)
    if len(open_workspaces(session, access.customer)) <= 1:
        raise HTTPException(status_code=409, detail="Keep at least one workspace.")
    workspace.archived_at = get_datetime_utc()
    session.add(workspace)
    session.commit()
    return read_workspaces(session, access)
