"""The archive of approved postings against Postgres, with a scripted LLM (no network): nothing is kept
until the customer turns the archive on for a workspace, free checks never are, postings are deleted three years
after the takedown date, and a customer only ever sees their own. Run `docker compose up -d db` and migrate first.
"""

import io
import secrets
import uuid
import zipfile
from collections.abc import Generator
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, delete, func, select

from app.api.archive import TORONTO, delete_on, kept_until, purge, today
from app.api.routes.checks import get_limits
from app.compliance.classification import Classification
from app.compliance.refiner import _Rewrite
from app.core.config import settings
from app.main import app
from app.models import (
    ArchivedFile,
    ArchivedPosting,
    Customer,
    PaidCheck,
    User,
    Workspace,
)
from tests.api.routes.test_workspaces import check, customer_headers, llm, save_profile  # noqa: F401
from tests.compliance.fake_llm import FakeLLM
from tests.compliance.test_api import MemoryLimits
from tests.compliance.test_inspector import POSTING
from tests.utils.accounts import make_customer, make_user

API = settings.API_V1_STR
PDF = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def apply_fixes(
    client: TestClient, llm: FakeLLM, headers: dict[str, str] | None = None, workspace: str | None = None  # noqa: F811
) -> dict[str, Any]:
    """Check the sample posting, write its fixes and apply them all: the final posting."""
    inspected = check(client, llm, headers or {}, workspace=workspace)
    llm.queue(_Rewrite, {"sentence": "2+ years of payroll experience"})
    llm.queue(Classification, {"canadian_experience": [{"sentence": 4, "label": "ok", "reason": "r"}], "vacancy": [], "ai": []})
    assert client.post(f"{API}/refine", json={"check_id": inspected["check_id"]}).status_code == 200
    final = client.post(f"{API}/patches/accept", json={"check_id": inspected["check_id"], "decisions": []})
    assert final.status_code == 200, final.text
    return {**final.json(), "workspace_id": inspected["workspace_id"]}


def turn_on(client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    return save_profile(client, headers, archive_postings=True)


def postings(db: Session, customer_id: uuid.UUID) -> list[ArchivedPosting]:
    db.expire_all()
    return list(db.exec(select(ArchivedPosting).where(ArchivedPosting.customer_id == customer_id)).all())


def customer_of(db: Session, headers: dict[str, str], client: TestClient) -> uuid.UUID:
    me = client.get(f"{API}/users/me", headers=headers).json()
    user = db.get(User, uuid.UUID(me["id"]))
    assert user is not None and user.customer_id is not None
    return user.customer_id


def archived_row(
    db: Session, customer: Customer, *, taken_down_on: date | None = None, saved: datetime | None = None,
    title: str = "Payroll Specialist",
) -> ArchivedPosting:  # fmt: skip
    """An archived posting straight in the database, saved on any day, for the retention tests."""
    workspace = db.exec(select(Workspace).where(Workspace.customer_id == customer.id)).first()
    if workspace is None:
        workspace = Workspace(customer_id=customer.id, archive_postings=True)
        db.add(workspace)
        db.flush()
    paid = PaidCheck(customer_id=customer.id, check_id=secrets.token_hex(8), title=title, status="compliant",
                     workspace_id=workspace.id)  # fmt: skip
    db.add(paid)
    db.flush()
    posting = ArchivedPosting(
        customer_id=customer.id, workspace_id=workspace.id, paid_check_id=paid.id, title=title, text=POSTING,
        taken_down_on=taken_down_on, delete_on=delete_on(taken_down_on),
        created_at=saved or datetime.now(TORONTO),
    )  # fmt: skip
    db.add(posting)
    db.commit()
    db.refresh(posting)
    return posting


# Opt-in, and what's saved


def test_the_archive_is_off_until_turned_on(client: TestClient, db: Session, llm: FakeLLM) -> None:  # noqa: F811
    headers = customer_headers(db)
    assert client.get(f"{API}/workspaces/current", headers=headers).json()["archive_postings"] is False
    final = apply_fixes(client, llm, headers)
    assert final["archived"] is None
    assert postings(db, customer_of(db, headers, client)) == []
    listed = client.get(f"{API}/archive/", headers=headers).json()
    assert listed["count"] == 0
    assert [w["archive_postings"] for w in listed["workspaces"]] == [False]


def test_applying_fixes_saves_the_final_posting(client: TestClient, db: Session, llm: FakeLLM) -> None:  # noqa: F811
    headers = customer_headers(db)
    assert turn_on(client, headers)["archive_postings"] is True
    final = apply_fixes(client, llm, headers)
    saved = final["archived"]["id"]
    [row] = postings(db, customer_of(db, headers, client))
    assert (str(row.id), row.text, row.title) == (saved, final["text"], "Payroll Specialist")
    assert (row.taken_down_on, row.delete_on) == (None, None)  # kept until it's marked taken down

    listed = client.get(f"{API}/archive/", headers=headers).json()
    assert listed["count"] == 1
    [summary] = listed["data"]
    assert summary["final_status"] == final["report"]["status"] and summary["files"] == 0
    assert summary["workspace_id"] == final["workspace_id"] and summary["kept_until"] is None

    edited = final["text"] + "\nApply by November 30."  # edited after applying: what actually goes up
    response = client.put(f"{API}/archive/{saved}/text", json={"text": edited}, headers=headers)
    assert response.status_code == 200 and response.json()["updated_at"] is not None
    assert client.get(f"{API}/archive/{saved}", headers=headers).json()["text"] == edited
    assert len(postings(db, customer_of(db, headers, client))) == 1  # one record per posting


def test_free_checks_never_store_the_posting(client: TestClient, db: Session, llm: FakeLLM) -> None:  # noqa: F811
    app.dependency_overrides[get_limits] = lambda: MemoryLimits(per_week=10, budget=Decimal(5))
    before = db.exec(select(func.count()).select_from(ArchivedPosting)).one()
    final = apply_fixes(client, llm)  # a visitor
    assert (final["archived"], final["workspace_id"]) == (None, None)
    db.expire_all()
    assert db.exec(select(func.count()).select_from(ArchivedPosting)).one() == before


def test_turning_the_archive_off_stops_saving(client: TestClient, db: Session, llm: FakeLLM) -> None:  # noqa: F811
    headers = customer_headers(db)
    turn_on(client, headers)
    apply_fixes(client, llm, headers)
    save_profile(client, headers, archive_postings=False)
    assert apply_fixes(client, llm, headers)["archived"] is None
    assert len(postings(db, customer_of(db, headers, client))) == 1  # what was saved stays


# Retention


def test_kept_for_three_years_after_the_takedown_date() -> None:
    assert kept_until(date(2026, 11, 30)) == date(2029, 11, 30)
    assert delete_on(date(2026, 11, 30)) == date(2029, 12, 1)
    assert kept_until(date(2028, 2, 29)) == date(2031, 2, 28)
    assert delete_on(None) is None


def test_postings_are_deleted_on_time(client: TestClient, db: Session) -> None:
    customer = make_customer(db)
    _, headers = make_user(db, customer)
    saved = datetime(2023, 9, 1, 12, tzinfo=TORONTO)
    due = archived_row(db, customer, taken_down_on=date(2023, 10, 21), saved=saved)  # kept until 2026-10-21
    tomorrow = archived_row(db, customer, taken_down_on=date(2023, 10, 22), saved=saved)
    still_up = archived_row(db, customer, saved=saved)
    db.add(ArchivedFile(posting_id=due.id, name="form.pdf", content_type="application/pdf", size=len(PDF), data=PDF))
    db.commit()

    purge(db, date(2026, 10, 21))  # the last day it's kept
    assert {p.id for p in postings(db, customer.id)} == {due.id, tomorrow.id, still_up.id}
    purge(db, date(2026, 10, 22))
    assert {p.id for p in postings(db, customer.id)} == {tomorrow.id, still_up.id}
    assert db.exec(select(ArchivedFile).where(ArchivedFile.posting_id == due.id)).all() == []  # its files went too
    purge(db, date(2026, 10, 23))
    purge(db, date(2099, 1, 1))  # no takedown date: kept
    assert {p.id for p in postings(db, customer.id)} == {still_up.id}

    # Reads skip a posting from its deletion day, even before the purge has run
    late = archived_row(db, customer, taken_down_on=today() - timedelta(days=3 * 366), saved=saved)
    assert late.delete_on is not None and late.delete_on <= today()
    ids = [p["id"] for p in client.get(f"{API}/archive/", headers=headers).json()["data"]]
    assert str(late.id) not in ids and str(still_up.id) in ids
    assert client.get(f"{API}/archive/{late.id}", headers=headers).status_code == 404


def test_marking_a_posting_taken_down(client: TestClient, db: Session) -> None:
    customer = make_customer(db)
    _, headers = make_user(db, customer)
    posting = archived_row(db, customer)
    url = f"{API}/archive/{posting.id}"
    down = client.patch(url, json={"taken_down_on": today().isoformat()}, headers=headers).json()
    assert down["taken_down_on"] == today().isoformat() and down["kept_until"] == kept_until(today()).isoformat()
    db.refresh(posting)
    assert posting.delete_on == kept_until(today()) + timedelta(days=1)

    # A slip of the year can't delete a posting at once, or push its deletion years out
    for day in (today() - timedelta(days=1), today() + timedelta(days=400)):
        response = client.patch(url, json={"taken_down_on": day.isoformat()}, headers=headers)
        assert response.status_code == 422, day
    back_up = client.patch(url, json={"taken_down_on": None}, headers=headers).json()
    assert (back_up["taken_down_on"], back_up["kept_until"]) == (None, None)
    db.refresh(posting)
    assert posting.delete_on is None


# Access


def test_customers_only_see_their_own_archive(client: TestClient, db: Session, llm: FakeLLM) -> None:  # noqa: F811
    mine = customer_headers(db)
    turn_on(client, mine)
    saved = apply_fixes(client, llm, mine)
    posting, workspace = saved["archived"]["id"], saved["workspace_id"]
    upload = client.post(f"{API}/archive/{posting}/files", files={"file": ("form.pdf", PDF, "application/pdf")}, headers=mine)
    document = upload.json()["id"]

    theirs = customer_headers(db)
    turn_on(client, theirs)
    apply_fixes(client, llm, theirs)
    listed = client.get(f"{API}/archive/", headers=theirs).json()
    assert posting not in [p["id"] for p in listed["data"]] and listed["count"] == 1
    assert workspace not in [w["id"] for w in listed["workspaces"]]
    for method, url, body in [
        ("get", f"/archive/{posting}", None), ("patch", f"/archive/{posting}", {"taken_down_on": None}),
        ("put", f"/archive/{posting}/text", {"text": "Mine now"}), ("delete", f"/archive/{posting}", None),
        ("get", f"/archive/{posting}/files/{document}", None), ("delete", f"/archive/{posting}/files/{document}", None),
        ("get", f"/archive/?workspace_id={workspace}", None), ("get", f"/archive/export?workspace_id={workspace}", None),
    ]:  # fmt: skip
        response = client.request(method, f"{API}{url}", json=body, headers=theirs)
        assert response.status_code == 404, (method, url, response.text)
    upload = client.post(f"{API}/archive/{posting}/files", files={"file": ("x.pdf", PDF, "application/pdf")}, headers=theirs)
    assert upload.status_code == 404
    assert client.get(f"{API}/archive/{posting}", headers=mine).json()["text"] == saved["text"]  # unchanged

    assert client.get(f"{API}/archive/").status_code == 401


def test_the_archive_is_listed_by_client(client: TestClient, db: Session, llm: FakeLLM) -> None:  # noqa: F811
    headers = customer_headers(db)
    turn_on(client, headers)
    first = apply_fixes(client, llm, headers)
    created = client.post(f"{API}/workspaces/", json={"name": "Maple Grocers"}, headers=headers).json()
    turn_on(client, headers)  # the new client's archive is off until turned on
    second = apply_fixes(client, llm, headers, workspace=created["id"])
    assert second["workspace_id"] == created["id"] and second["archived"] is not None

    by_client = client.get(f"{API}/archive/", params={"workspace_id": created["id"]}, headers=headers).json()
    assert [p["id"] for p in by_client["data"]] == [second["archived"]["id"]]
    assert by_client["data"][0]["workspace_name"] == "Maple Grocers"
    everything = client.get(f"{API}/archive/", headers=headers).json()
    assert [p["id"] for p in everything["data"]] == [second["archived"]["id"], first["archived"]["id"]]

    # A client's workspace archived (hidden from the switcher) keeps its postings in the archive
    client.post(f"{API}/workspaces/{created['id']}/archive", headers=headers)
    workspaces = client.get(f"{API}/archive/", headers=headers).json()["workspaces"]
    assert {(w["name"], w["archived"]) for w in workspaces} >= {("Maple Grocers", True)}


def test_search_by_title_and_saved_date(client: TestClient, db: Session) -> None:
    customer = make_customer(db)
    _, headers = make_user(db, customer)
    old = archived_row(db, customer, title="Payroll Specialist", saved=datetime(2026, 3, 2, 23, 30, tzinfo=TORONTO))
    new = archived_row(db, customer, title="Warehouse Associate (Night Shift)", saved=datetime(2026, 9, 15, 9, tzinfo=TORONTO))

    def ids(**query: str) -> list[str]:
        return [p["id"] for p in client.get(f"{API}/archive/", params=query, headers=headers).json()["data"]]

    assert ids(q="payroll") == [str(old.id)]
    assert ids(q="night warehouse") == [str(new.id)]  # every word, any order
    assert ids(q="100%") == []
    assert ids(saved_from="2026-03-02", saved_to="2026-03-02") == [str(old.id)]  # Toronto days, not UTC
    assert ids(saved_from="2026-03-03") == [str(new.id)]
    assert ids() == [str(new.id), str(old.id)]


# Documents, read-only after the plan ends, and deletion


def test_documents_the_posting_links_to(client: TestClient, db: Session) -> None:
    customer = make_customer(db)
    _, headers = make_user(db, customer)
    posting = archived_row(db, customer)
    url = f"{API}/archive/{posting.id}/files"

    def upload(name: str, data: bytes) -> Any:
        return client.post(url, files={"file": (name, data, "application/octet-stream")}, headers=headers)

    stored = upload("Application form.pdf", PDF)
    assert stored.status_code == 201 and stored.json()["content_type"] == "application/pdf"
    download = client.get(f"{url}/{stored.json()['id']}", headers=headers)
    assert download.content == PDF and download.headers["content-type"] == "application/pdf"
    assert "attachment" in download.headers["content-disposition"]

    assert upload("form.exe", b"MZ\x90\x00").status_code == 422
    assert upload("fake.pdf", b"<html>not a pdf</html>").status_code == 422  # the bytes have to match
    assert upload("big.pdf", b"%PDF-" + b"0" * (10 * 1024 * 1024)).status_code == 413
    for n in range(4):
        assert upload(f"page-{n}.png", b"\x89PNG\r\n\x1a\n" + b"0" * 16).status_code == 201
    assert upload("sixth.jpg", b"\xff\xd8\xff\xe0").status_code == 409

    form = client.patch(f"{API}/archive/{posting.id}", json={"application_form": "Name\nEmail\nResume"}, headers=headers)
    detail = form.json()
    assert detail["application_form"] == "Name\nEmail\nResume" and len(detail["documents"]) == 5
    assert client.delete(f"{url}/{stored.json()['id']}", headers=headers).status_code == 200
    assert client.get(f"{API}/archive/{posting.id}", headers=headers).json()["files"] == 4


def test_deleting_the_account_deletes_the_archive(client: TestClient, db: Session) -> None:
    customer = make_customer(db)
    user, headers = make_user(db, customer)
    posting_id, customer_id, user_id = archived_row(db, customer).id, customer.id, user.id
    db.add(ArchivedFile(posting_id=posting_id, name="form.pdf", content_type="application/pdf", size=len(PDF), data=PDF))
    db.commit()
    assert client.delete(f"{API}/users/me", headers=headers).status_code == 200
    db.expire_all()
    assert db.get(ArchivedPosting, posting_id) is None
    assert db.exec(select(func.count()).select_from(ArchivedFile).where(col(ArchivedFile.posting_id) == posting_id)).one() == 0
    assert db.get(Customer, customer_id) is None  # the account goes with its last user
    assert db.get(User, user_id) is None


def test_a_workspace_downloads_as_a_zip(client: TestClient, db: Session) -> None:
    customer = make_customer(db)
    _, headers = make_user(db, customer)
    first = archived_row(db, customer, title="Payroll Specialist", taken_down_on=today())
    second = archived_row(db, customer, title="Payroll Specialist")  # same title: its own folder
    client.patch(f"{API}/archive/{second.id}", json={"application_form": "Name\nEmail"}, headers=headers)
    client.post(f"{API}/archive/{second.id}/files", files={"file": ("Benefits.pdf", PDF, "application/pdf")}, headers=headers)

    response = client.get(f"{API}/archive/export", params={"workspace_id": str(first.workspace_id)}, headers=headers)
    assert response.status_code == 200 and response.headers["content-type"] == "application/zip"
    assert "attachment" in response.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = set(archive.namelist())
        day = datetime.now(TORONTO).date().isoformat()
        assert names == {
            "index.html", f"{day} Payroll Specialist/posting.html", f"{day} Payroll Specialist (2)/posting.html",
            f"{day} Payroll Specialist (2)/Benefits.pdf",
        }  # fmt: skip
        assert archive.read(f"{day} Payroll Specialist (2)/Benefits.pdf") == PDF
        page = archive.read(f"{day} Payroll Specialist (2)/posting.html").decode()
        assert "Mississauga, ON (hybrid)" in page and "Application form" in page and 'href="Benefits.pdf"' in page
        taken_down = archive.read(f"{day} Payroll Specialist/posting.html").decode()
        assert f"{kept_until(today()):%B}" in taken_down and "Kept until" in taken_down
        assert "Payroll Specialist" in archive.read("index.html").decode()


@pytest.fixture(autouse=True, scope="module")
def clean_up(db: Session) -> Generator[None]:
    """Customers go at the end, and their archives with them (the database cascades)."""
    yield
    db.execute(delete(PaidCheck))
    for user in db.exec(select(User).where(col(User.customer_id).is_not(None))).all():
        db.delete(user)
    for user in db.exec(select(User).where(col(User.email).like("%@agency.example"))).all():
        db.delete(user)
    db.commit()
    db.execute(delete(Workspace))
    db.execute(delete(Customer))
    db.commit()
