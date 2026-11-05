"""The archive of approved postings: an account's record of every posting they applied fixes to, for the three
years the ESA keeps it after the posting comes down (s. 15 (7.1)). Off until the account turns it on for a
workspace; visitors' free checks never reach it. A posting is deleted three years after the takedown date the user
enters, and kept until they enter one.
"""

import html
import io
import re
import threading
import time
import uuid
import zipfile
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import ColumnElement, or_
from sqlmodel import Session, col, delete, select

from app.api.accounts import account_for
from app.api.workspaces import label
from app.core.db import engine
from app.models import (
    ArchivedFile,
    ArchivedPosting,
    Customer,
    PaidCheck,
    User,
    Workspace,
    get_datetime_utc,
)

TORONTO = ZoneInfo("America/Toronto")
KEPT_YEARS = 3
MAX_FILES = 5  # per posting
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TEXT_CHARS = 20_000  # the posting as edited, and the application form
PURGE_EVERY = 600  # seconds between purges in one process
# What an upload may be: its extension, the type it's served with, and how its first bytes start
FILE_TYPES = {
    ".pdf": ("application/pdf", b"%PDF-"),
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", b"PK\x03\x04"),
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
}


def today() -> date:
    return datetime.now(TORONTO).date()


def toronto_date(moment: datetime) -> date:
    return moment.astimezone(TORONTO).date()


def kept_until(taken_down_on: date) -> date:
    """The last day a posting taken down on that day must be kept: three years on. 29 February counts to the
    28th."""
    try:
        return taken_down_on.replace(year=taken_down_on.year + KEPT_YEARS)
    except ValueError:
        return taken_down_on.replace(year=taken_down_on.year + KEPT_YEARS, day=28)


def delete_on(taken_down_on: date | None) -> date | None:
    return kept_until(taken_down_on) + timedelta(days=1) if taken_down_on else None


def kept(on: date) -> ColumnElement[bool]:
    """Postings not yet due for deletion on that day: reads skip them even before the purge runs."""
    return or_(col(ArchivedPosting.delete_on).is_(None), col(ArchivedPosting.delete_on) > on)


# Saving


def save_applied(session: Session, check_id: str, workspace_id: uuid.UUID | None, text: str) -> ArchivedPosting | None:
    """Keep the posting an account just applied fixes to, if the check was a signed-in one and its workspace's
    archive is on. Applying again in the same check replaces the text."""
    workspace = session.get(Workspace, workspace_id) if workspace_id else None
    if workspace is None or not workspace.archive_postings:
        return None
    # Locked, so two applies at once can't both add a posting for the check
    paid = session.exec(select(PaidCheck).where(PaidCheck.check_id == check_id).with_for_update()).first()
    if paid is None or paid.customer_id != workspace.customer_id:
        return None
    posting = session.exec(select(ArchivedPosting).where(ArchivedPosting.paid_check_id == paid.id)).first()
    if posting is None:
        posting = ArchivedPosting(
            customer_id=workspace.customer_id, workspace_id=workspace.id, paid_check_id=paid.id, title=paid.title,
            text=text[:MAX_TEXT_CHARS],
        )  # fmt: skip
    else:
        posting.text, posting.updated_at = text[:MAX_TEXT_CHARS], get_datetime_utc()
    session.add(posting)
    session.commit()
    session.refresh(posting)
    return posting


# Deleting


def purge(session: Session, on: date) -> int:
    """Delete the postings due on that day, and their files (the database cascades). Returns how many went."""
    result = session.exec(delete(ArchivedPosting).where(col(ArchivedPosting.delete_on) <= on))
    session.commit()
    return result.rowcount  # type: ignore[attr-defined]


_last_purge = 0.0
_purge_lock = threading.Lock()


def purge_soon() -> None:
    """Purge after a request, at most every PURGE_EVERY seconds per process: any check or archive visit runs
    it, so deletion doesn't wait for the customer to come back. Reads skip due postings meanwhile."""
    global _last_purge
    with _purge_lock:
        if time.monotonic() - _last_purge < PURGE_EVERY:
            return
        _last_purge = time.monotonic()
    with Session(engine) as session:
        purge(session, today())


# Access


def archive_owner(session: Session, user: User) -> Customer:
    """The account whose archive the user sees."""
    return account_for(session, user)


def owned_posting(session: Session, customer: Customer, posting_id: uuid.UUID) -> ArchivedPosting:
    posting = session.exec(
        select(ArchivedPosting).where(
            ArchivedPosting.id == posting_id, ArchivedPosting.customer_id == customer.id, kept(today())
        )
    ).first()  # fmt: skip
    if posting is None:
        raise HTTPException(status_code=404, detail="Posting not found.")
    return posting


def owned_workspace(session: Session, customer: Customer, workspace_id: uuid.UUID) -> Workspace:
    """Any of the customer's workspaces, archived ones included: their postings stay in the archive."""
    workspace = session.get(Workspace, workspace_id)
    if workspace is None or workspace.customer_id != customer.id:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    return workspace


def file_type(name: str, head: bytes) -> str:
    """The type an upload is served with, or 422 when it isn't a PDF, DOCX, PNG or JPG."""
    extension = name[name.rfind(".") :].lower() if "." in name else ""
    if extension not in FILE_TYPES or not head.startswith(FILE_TYPES[extension][1]):
        raise HTTPException(status_code=422, detail="Upload a PDF, Word (.docx), PNG or JPG file.")
    return FILE_TYPES[extension][0]


# Export: a zip per workspace


def _day(value: date) -> str:
    return f"{value:%B} {value.day}, {value.year}"


def _folder(posting: ArchivedPosting, taken: set[str]) -> str:
    title = re.sub(r"[^\w\- ]+", "", posting.title or "Untitled posting").strip()[:60] or "Untitled posting"
    folder = base = f"{toronto_date(posting.created_at).isoformat()} {title}"
    n = 2
    while folder in taken:
        folder, n = f"{base} ({n})", n + 1
    taken.add(folder)
    return folder


def _file_name(name: str, taken: set[str]) -> str:
    """A document's name in its folder: path characters replaced, numbered when two share a name."""
    safe = re.sub(r'[\\/:*?"<>|]+', "_", name).strip() or "document"
    stem, dot, extension = safe.rpartition(".")
    if not dot:
        stem, extension = safe, ""
    candidate, n = safe, 2
    while candidate in taken or candidate == "posting.html":
        candidate = f"{stem} ({n}).{extension}" if extension else f"{stem} ({n})"
        n += 1
    taken.add(candidate)
    return candidate


_STYLE = (
    "body{font:16px/1.55 system-ui,sans-serif;max-width:48rem;margin:2rem auto;padding:0 1rem;color:#1a1a1a}"
    "pre{white-space:pre-wrap;font:inherit;border:1px solid #ddd;border-radius:8px;padding:1rem}"
    "dt{font-weight:600}dd{margin:0 0 .5rem}table{border-collapse:collapse;width:100%}"
    "td,th{border-bottom:1px solid #ddd;padding:.4rem;text-align:left;vertical-align:top}"
)


def _page(title: str, body: str) -> str:
    return (
        f'<!doctype html><html lang="en"><meta charset="utf-8"><title>{html.escape(title)}</title>'
        f"<style>{_STYLE}</style><body>{body}</body></html>"
    )


def _dates(posting: ArchivedPosting) -> list[tuple[str, str]]:
    rows = [("Saved to the archive", _day(toronto_date(posting.created_at)))]
    if posting.updated_at:
        rows.append(("Last edited", _day(toronto_date(posting.updated_at))))
    if posting.taken_down_on:
        rows += [("Taken down", _day(posting.taken_down_on)), ("Kept until", _day(kept_until(posting.taken_down_on)))]
    else:
        rows.append(("Taken down", "Still up: kept until 3 years after you mark it taken down"))
    return rows


def _posting_page(posting: ArchivedPosting, client: str, files: list[str]) -> str:
    title = posting.title or "Untitled posting"
    facts = "".join(f"<dt>{html.escape(k)}</dt><dd>{html.escape(v)}</dd>" for k, v in [("Client", client), *_dates(posting)])
    body = f"<h1>{html.escape(title)}</h1><dl>{facts}</dl><h2>Posting</h2><pre>{html.escape(posting.text)}</pre>"
    if posting.application_form:
        body += f"<h2>Application form</h2><pre>{html.escape(posting.application_form)}</pre>"
    if files:
        links = "".join(f'<li><a href="{html.escape(name)}">{html.escape(name)}</a></li>' for name in files)
        body += f"<h2>Linked documents</h2><ul>{links}</ul>"
    return _page(title, body)


class _Chunks(io.RawIOBase):
    """A write-only stream the zip is written into, emptied as the response streams it."""

    def __init__(self) -> None:
        self.chunks: list[bytes] = []

    def writable(self) -> bool:
        return True

    def write(self, data: bytes) -> int:  # type: ignore[override]
        self.chunks.append(bytes(data))
        return len(data)

    def take(self) -> bytes:
        out = b"".join(self.chunks)
        self.chunks.clear()
        return out


def export_zip(customer_id: uuid.UUID, workspace_id: uuid.UUID) -> Iterator[bytes]:
    """A zip of a workspace's archive: an index page, then a folder per posting with its page and its documents.
    Streamed, loading one document at a time, in its own session (the request's is closed by then)."""
    sink = _Chunks()
    with Session(engine) as session, zipfile.ZipFile(sink, "w", zipfile.ZIP_DEFLATED) as archive:
        workspace = session.get(Workspace, workspace_id)
        client = label(workspace) if workspace else ""
        postings = session.exec(
            select(ArchivedPosting)
            .where(ArchivedPosting.customer_id == customer_id, ArchivedPosting.workspace_id == workspace_id, kept(today()))
            .order_by(col(ArchivedPosting.created_at))
        ).all()  # fmt: skip
        folders: set[str] = set()
        rows = []
        for posting in postings:
            folder = _folder(posting, folders)
            files = session.exec(
                select(ArchivedFile.id, ArchivedFile.name)
                .where(ArchivedFile.posting_id == posting.id)
                .order_by(col(ArchivedFile.created_at))
            ).all()  # fmt: skip
            names: set[str] = set()
            written = []
            for file_id, name in files:
                data = session.exec(select(ArchivedFile.data).where(ArchivedFile.id == file_id)).one()
                written.append(_file_name(name, names))
                archive.writestr(f"{folder}/{written[-1]}", data)
                yield sink.take()
            archive.writestr(f"{folder}/posting.html", _posting_page(posting, client, written))
            down = _day(posting.taken_down_on) if posting.taken_down_on else "Still up"
            rows.append(
                f'<tr><td><a href="{html.escape(folder)}/posting.html">{html.escape(posting.title or "Untitled posting")}</a></td>'
                f"<td>{_day(toronto_date(posting.created_at))}</td><td>{down}</td>"
                f"<td>{_day(kept_until(posting.taken_down_on)) if posting.taken_down_on else ''}</td></tr>"
            )
            yield sink.take()
        table = "".join(rows) or '<tr><td colspan="4">No postings in the archive.</td></tr>'
        archive.writestr("index.html", _page(
            f"Archive: {client}",
            f"<h1>Archive of approved postings: {html.escape(client)}</h1>"
            f"<p>Exported from CheckON on {_day(today())}.</p>"
            f"<table><tr><th>Posting</th><th>Saved</th><th>Taken down</th><th>Kept until</th></tr>{table}</table>",
        ))  # fmt: skip
    yield sink.take()
