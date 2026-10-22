"""The archive of approved postings (PRD FR11): list a customer's archived postings by workspace and search them,
view one, save an edit, add the application form and linked documents, mark it taken down, delete it, and
download a workspace's archive as a zip. Postings are saved by applying fixes (routes/checks.py).
"""

import uuid
from datetime import date, datetime, time, timedelta
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import col, func, or_, select

from app.api.archive import (
    MAX_FILE_BYTES,
    MAX_FILES,
    MAX_TEXT_CHARS,
    TORONTO,
    archive_owner,
    delete_on,
    export_zip,
    file_type,
    kept,
    kept_until,
    owned_posting,
    owned_workspace,
    purge_soon,
    require_plan,
    today,
    toronto_date,
)
from app.api.billing import Plan
from app.api.deps import CurrentUser, SessionDep
from app.api.workspaces import label
from app.models import (
    ArchivedFile,
    ArchivedPosting,
    Customer,
    Message,
    PaidCheck,
    Workspace,
    get_datetime_utc,
)

router = APIRouter(prefix="/archive", tags=["archive"])


def get_owner(session: SessionDep, user: CurrentUser, background: BackgroundTasks) -> tuple[Customer, Plan | None]:
    background.add_task(purge_soon)
    return archive_owner(session, user)


OwnerDep = Annotated[tuple[Customer, Plan | None], Depends(get_owner)]


class ArchiveWorkspace(BaseModel):
    id: uuid.UUID
    name: str
    archive_postings: bool  # new checks are saved here
    archived: bool  # the workspace is hidden from the switcher; its postings stay


class ArchivedPostingSummary(BaseModel):
    id: uuid.UUID
    created_at: datetime  # when it was saved
    updated_at: datetime | None  # when a saved edit replaced the text
    title: str | None
    final_status: str | None  # the check's result after the fixes
    workspace_id: uuid.UUID
    workspace_name: str
    taken_down_on: date | None
    kept_until: date | None  # the last day it's kept: 3 years after taken_down_on
    files: int


class ArchivedPostingsPublic(BaseModel):
    data: list[ArchivedPostingSummary]  # newest first
    count: int
    workspaces: list[ArchiveWorkspace]  # open ones, and archived ones that still have postings
    read_only: bool  # the plan has ended: nothing new can be saved


class ArchivedFilePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    name: str
    content_type: str
    size: int


class ArchivedPostingPublic(ArchivedPostingSummary):
    text: str
    application_form: str | None
    documents: list[ArchivedFilePublic]
    read_only: bool


class ArchivedPostingUpdate(BaseModel):
    """Only the fields sent are changed. A takedown date sets when the posting is deleted; null means still up."""

    model_config = ConfigDict(extra="forbid")
    taken_down_on: date | None = None
    application_form: str | None = Field(default=None, max_length=MAX_TEXT_CHARS)


class ArchivedTextIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)


def _summary(posting: ArchivedPosting, workspace: Workspace, final_status: str | None, files: int) -> dict[str, Any]:
    return {
        **posting.model_dump(exclude={"text", "application_form"}), "final_status": final_status,
        "workspace_name": label(workspace), "files": files,
        "kept_until": kept_until(posting.taken_down_on) if posting.taken_down_on else None,
    }  # fmt: skip


def _counts(session: SessionDep, posting_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    rows = session.exec(
        select(ArchivedFile.posting_id, func.count())
        .where(col(ArchivedFile.posting_id).in_(posting_ids))
        .group_by(col(ArchivedFile.posting_id))
    ).all()  # fmt: skip
    return dict(rows)


def _documents(session: SessionDep, posting: ArchivedPosting) -> list[ArchivedFilePublic]:
    rows = session.exec(
        select(ArchivedFile.id, ArchivedFile.created_at, ArchivedFile.name, ArchivedFile.content_type, ArchivedFile.size)
        .where(ArchivedFile.posting_id == posting.id)
        .order_by(col(ArchivedFile.created_at))
    ).all()  # fmt: skip
    return [ArchivedFilePublic.model_validate(row._mapping) for row in rows]


def _public(session: SessionDep, posting: ArchivedPosting, plan: Plan | None) -> ArchivedPostingPublic:
    workspace = session.get(Workspace, posting.workspace_id)
    paid = session.get(PaidCheck, posting.paid_check_id)
    documents = _documents(session, posting)
    assert workspace is not None
    return ArchivedPostingPublic.model_validate({
        **_summary(posting, workspace, paid.final_status if paid else None, len(documents)),
        "text": posting.text, "application_form": posting.application_form, "documents": documents,
        "read_only": plan is None,
    })  # fmt: skip


def _start_of(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=TORONTO)


@router.get("/", response_model=ArchivedPostingsPublic)
def read_archive(
    session: SessionDep, owner: OwnerDep, workspace_id: uuid.UUID | None = None,
    q: Annotated[str | None, Query(max_length=255)] = None, saved_from: date | None = None,
    saved_to: date | None = None, skip: int = 0, limit: int = 50,
) -> Any:  # fmt: skip
    """The customer's archived postings, newest first: all workspaces or one, searched by job title and the day
    they were saved (Toronto time)."""
    customer, plan = owner
    mine = [col(ArchivedPosting.customer_id) == customer.id, kept(today())]
    if workspace_id is not None:
        mine.append(col(ArchivedPosting.workspace_id) == owned_workspace(session, customer, workspace_id).id)
    if q and (words := q.split()):
        for word in words:
            escaped = word.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            mine.append(col(ArchivedPosting.title).ilike(f"%{escaped}%", escape="\\"))
    if saved_from is not None:
        mine.append(col(ArchivedPosting.created_at) >= _start_of(saved_from))
    if saved_to is not None:
        mine.append(col(ArchivedPosting.created_at) < _start_of(saved_to + timedelta(days=1)))
    count = session.exec(select(func.count()).select_from(ArchivedPosting).where(*mine)).one()
    rows = session.exec(
        select(ArchivedPosting, Workspace, PaidCheck.final_status)
        .join(Workspace, col(ArchivedPosting.workspace_id) == Workspace.id)
        .join(PaidCheck, col(ArchivedPosting.paid_check_id) == PaidCheck.id)
        .where(*mine)
        .order_by(col(ArchivedPosting.created_at).desc())
        .offset(skip)
        .limit(min(limit, 100))
    ).all()  # fmt: skip
    files = _counts(session, [posting.id for posting, _, _ in rows])
    data = [
        ArchivedPostingSummary.model_validate(_summary(posting, workspace, status, files.get(posting.id, 0)))
        for posting, workspace, status in rows
    ]
    with_postings = select(ArchivedPosting.workspace_id).where(ArchivedPosting.customer_id == customer.id)
    workspaces = session.exec(
        select(Workspace)
        .where(
            Workspace.customer_id == customer.id,
            or_(col(Workspace.archived_at).is_(None), col(Workspace.id).in_(with_postings)),
        )
        .order_by(col(Workspace.created_at))
    ).all()  # fmt: skip
    return ArchivedPostingsPublic(
        data=data, count=count, read_only=plan is None,
        workspaces=[
            ArchiveWorkspace(id=w.id, name=label(w), archive_postings=w.archive_postings, archived=w.archived_at is not None)
            for w in workspaces
        ],
    )  # fmt: skip


@router.get("/export", response_class=StreamingResponse)
def export_archive(session: SessionDep, owner: OwnerDep, workspace_id: uuid.UUID) -> Any:
    """A workspace's archive as a zip: an index page, and a folder per posting with the posting, its
    application form and its linked documents."""
    customer, _ = owner
    workspace = owned_workspace(session, customer, workspace_id)
    name = f"CheckON archive - {label(workspace)} - {today().isoformat()}.zip"
    return StreamingResponse(
        export_zip(customer.id, workspace.id), media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"},
    )  # fmt: skip


@router.get("/{posting_id}", response_model=ArchivedPostingPublic)
def read_archived_posting(posting_id: uuid.UUID, session: SessionDep, owner: OwnerDep) -> Any:
    customer, plan = owner
    return _public(session, owned_posting(session, customer, posting_id), plan)


@router.patch("/{posting_id}", response_model=ArchivedPostingPublic)
def update_archived_posting(
    posting_id: uuid.UUID, body: ArchivedPostingUpdate, session: SessionDep, owner: OwnerDep
) -> Any:
    """Mark a posting taken down (or still up), or save its application form's text. A takedown date can be
    set after the plan ends, so the posting is still deleted on time; the form can't."""
    customer, plan = owner
    posting = owned_posting(session, customer, posting_id)
    update = body.model_dump(exclude_unset=True)
    if "application_form" in update:
        require_plan(plan)
        posting.application_form = (update["application_form"] or "").strip() or None
    if "taken_down_on" in update:
        down = update["taken_down_on"]
        if down is not None and not toronto_date(posting.created_at) <= down <= today() + timedelta(days=366):
            raise HTTPException(
                status_code=422,
                detail="The takedown date can't be before the day the posting was saved, or more than a year ahead.",
            )
        posting.taken_down_on, posting.delete_on = down, delete_on(down)
    session.add(posting)
    session.commit()
    session.refresh(posting)
    return _public(session, posting, plan)


@router.put("/{posting_id}/text", response_model=ArchivedPostingPublic)
def save_archived_text(posting_id: uuid.UUID, body: ArchivedTextIn, session: SessionDep, owner: OwnerDep) -> Any:
    """Replace the archived text with the posting as edited after applying the fixes: what actually goes up."""
    customer, plan = owner
    require_plan(plan)
    posting = owned_posting(session, customer, posting_id)
    posting.text, posting.updated_at = body.text, get_datetime_utc()
    session.add(posting)
    session.commit()
    session.refresh(posting)
    return _public(session, posting, plan)


@router.delete("/{posting_id}", response_model=Message)
def delete_archived_posting(posting_id: uuid.UUID, session: SessionDep, owner: OwnerDep) -> Any:
    """Delete a posting and its documents now, before its three years are up."""
    customer, _ = owner
    session.delete(owned_posting(session, customer, posting_id))
    session.commit()
    return Message(message="Deleted from the archive.")


@router.post("/{posting_id}/files", response_model=ArchivedFilePublic, status_code=201)
def upload_archived_file(posting_id: uuid.UUID, file: UploadFile, session: SessionDep, owner: OwnerDep) -> Any:
    """Add a document the posting links to: a PDF, Word (.docx), PNG or JPG file up to 10 MB, 5 per posting."""
    customer, plan = owner
    require_plan(plan)
    posting = owned_posting(session, customer, posting_id)
    if session.exec(select(func.count()).select_from(ArchivedFile).where(ArchivedFile.posting_id == posting.id)).one() >= MAX_FILES:
        raise HTTPException(status_code=409, detail=f"A posting can have {MAX_FILES} documents. Delete one first.")
    data = file.file.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="That file is over 10 MB.")
    if not data:
        raise HTTPException(status_code=422, detail="That file is empty.")
    name = " ".join((file.filename or "").replace("\\", "/").rsplit("/", 1)[-1].split())[:255] or "document"
    stored = ArchivedFile(posting_id=posting.id, name=name, content_type=file_type(name, data[:8]), size=len(data), data=data)
    session.add(stored)
    session.commit()
    session.refresh(stored)
    return ArchivedFilePublic.model_validate(stored)


@router.get("/{posting_id}/files/{file_id}", response_class=Response)
def download_archived_file(posting_id: uuid.UUID, file_id: uuid.UUID, session: SessionDep, owner: OwnerDep) -> Any:
    customer, _ = owner
    posting = owned_posting(session, customer, posting_id)
    stored = session.get(ArchivedFile, file_id)
    if stored is None or stored.posting_id != posting.id:
        raise HTTPException(status_code=404, detail="Document not found.")
    return Response(
        stored.data, media_type=stored.content_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(stored.name)}"},
    )  # fmt: skip


@router.delete("/{posting_id}/files/{file_id}", response_model=Message)
def delete_archived_file(posting_id: uuid.UUID, file_id: uuid.UUID, session: SessionDep, owner: OwnerDep) -> Any:
    customer, _ = owner
    posting = owned_posting(session, customer, posting_id)
    stored = session.get(ArchivedFile, file_id)
    if stored is None or stored.posting_id != posting.id:
        raise HTTPException(status_code=404, detail="Document not found.")
    session.delete(stored)
    session.commit()
    return Message(message="Document deleted.")
