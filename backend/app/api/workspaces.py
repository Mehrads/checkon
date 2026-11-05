"""Company profiles and client workspaces: the facts a signed-in account's checks start from, so a check doesn't
ask for them or search for the employer's size. An account starts with one empty workspace and can add one per
client (for recruiters and agencies), each with its own profile. Company facts only: the posting text is never
stored.
"""

import uuid
from typing import Literal

from fastapi import HTTPException
from sqlmodel import Session, col, delete, func, select

from app.api.accounts import Access
from app.compliance.models import Context
from app.models import Audit, Customer, PaidCheck, User, Workspace

Wording = Literal["formal", "plain"]
MAX_WORKSPACES = 100  # open at once, per customer


def label(workspace: Workspace) -> str:
    return workspace.name or workspace.employer_name or "Your company"


def open_workspaces(session: Session, customer: Customer) -> list[Workspace]:
    """Workspaces not archived, oldest first. A customer without one gets an empty one. The customer row is
    locked before creating it, so two requests at once can't both create it."""
    mine = (
        select(Workspace)
        .where(Workspace.customer_id == customer.id, col(Workspace.archived_at).is_(None))
        .order_by(col(Workspace.created_at))
    )
    if found := list(session.exec(mine).all()):
        return found
    session.exec(select(Customer).where(Customer.id == customer.id).with_for_update()).one()
    if not (found := list(session.exec(mine).all())):
        found = [Workspace(customer_id=customer.id)]
        session.add(found[0])
    session.commit()
    for workspace in found:
        session.refresh(workspace)
    return found


def current_workspace(session: Session, access: Access, requested: uuid.UUID | None = None) -> Workspace:
    """The workspace a check or the profile page uses: the one asked for, else the one the user last picked,
    else the first."""
    workspaces = open_workspaces(session, access.customer)
    by_id = {workspace.id: workspace for workspace in workspaces}
    if requested is not None:
        if requested not in by_id:
            raise HTTPException(status_code=409, detail="That workspace was archived. Pick another one and try again.")
        return by_id[requested]
    picked = access.user.workspace_id
    return by_id[picked] if picked in by_id else workspaces[0]


def profile_context(workspace: Workspace) -> Context:
    """The check's starting context: what the profile says, and None (ask or search) for the rest."""
    return Context(
        headcount=workspace.headcount,
        meets_headcount_threshold=workspace.meets_headcount_threshold if workspace.headcount is None else None,
        uses_ai_in_hiring=workspace.uses_ai_in_hiring,
    )


def wording(workspace: Workspace | None) -> Wording:
    return "plain" if workspace is not None and workspace.wording == "plain" else "formal"


def forget_profiles(session: Session, customer_id: uuid.UUID | None) -> None:
    """When an account's last user is deleted, everything the account kept goes too: company profiles, careers
    page audits, check history and the archive. Call after deleting the user, before committing."""
    if customer_id is None:
        return
    session.flush()
    users = session.exec(select(func.count()).select_from(User).where(User.customer_id == customer_id)).one()
    if users == 0:
        session.exec(delete(Audit).where(col(Audit.customer_id) == customer_id))
        session.exec(delete(Workspace).where(col(Workspace.customer_id) == customer_id))
        session.exec(delete(PaidCheck).where(col(PaidCheck.customer_id) == customer_id))
        customer = session.get(Customer, customer_id)
        if customer is not None:
            session.delete(customer)  # the archive goes with it (ON DELETE CASCADE)
