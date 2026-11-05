"""The signed-in account: its checks for the last 30 days, against the server's limit if it has one, and the
history of what it checked (date, job title, result and workspace; never the posting text)."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from sqlmodel import col, func, select

from app.api.accounts import account_for, checks_used
from app.api.deps import CurrentUser, SessionDep
from app.api.workspaces import label
from app.core.config import settings
from app.models import PaidCheck, Workspace, get_datetime_utc

router = APIRouter(prefix="/account", tags=["account"])


class AccountOut(BaseModel):
    checks_used: int  # in the last 30 days
    checks_limit: int | None  # in any 30 days; None: no limit
    signup_open: bool  # anyone can make an account on this server


class CheckRecordPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    title: str | None
    status: str
    final_status: str | None
    workspace_id: uuid.UUID | None = None  # archived workspaces included
    workspace_name: str | None = None


class CheckRecordsPublic(BaseModel):
    data: list[CheckRecordPublic]
    count: int


@router.get("", response_model=AccountOut)
def read_account(session: SessionDep, user: CurrentUser) -> Any:
    customer = account_for(session, user)
    limit = settings.ACCOUNT_CHECKS_PER_30_DAYS
    return AccountOut(
        checks_used=checks_used(session, customer.id, get_datetime_utc()),
        checks_limit=limit if limit > 0 else None,
        signup_open=settings.SIGNUP_OPEN,
    )


@router.get("/checks", response_model=CheckRecordsPublic)
def read_account_checks(
    session: SessionDep, user: CurrentUser, skip: int = 0, limit: int = 50, workspace_id: uuid.UUID | None = None
) -> Any:
    """The account's checks, newest first, for all workspaces or one."""
    if user.customer_id is None:
        return CheckRecordsPublic(data=[], count=0)
    mine = [col(PaidCheck.customer_id) == user.customer_id]
    if workspace_id is not None:
        mine.append(col(PaidCheck.workspace_id) == workspace_id)
    count = session.exec(select(func.count()).select_from(PaidCheck).where(*mine)).one()
    rows = session.exec(
        select(PaidCheck, Workspace)
        .join(Workspace, col(PaidCheck.workspace_id) == Workspace.id, isouter=True)
        .where(*mine)
        .order_by(col(PaidCheck.created_at).desc())
        .offset(skip)
        .limit(min(limit, 100))
    ).all()
    data = [
        CheckRecordPublic.model_validate(check).model_copy(update={"workspace_name": label(ws) if ws else None})
        for check, ws in rows
    ]
    return CheckRecordsPublic(data=data, count=count)
