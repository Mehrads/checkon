"""Company profiles (PRD FR2) and client workspaces (FR10): the facts a paying customer's checks start from, so
a check doesn't ask for them or search for the employer's size. Starter has one profile, created empty on first
use. Agency has a workspace per client, each with its own profile; the plan's checks are shared by all of them.
Company facts only: the posting text is never stored.
"""

import uuid
from typing import Literal

from fastapi import HTTPException
from sqlmodel import Session, col, delete, func, select

from app.api.billing import PlanAccess
from app.compliance.models import Context
from app.models import Audit, Customer, User, Workspace

Wording = Literal["formal", "plain"]
MAX_WORKSPACES = 100  # open at once, per customer


def has_workspaces(access: PlanAccess) -> bool:
    """Several client workspaces and a switcher: Agency only."""
    return access.plan.id == "agency"


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


def current_workspace(session: Session, access: PlanAccess, requested: uuid.UUID | None = None) -> Workspace:
    """The workspace a check or the profile page uses: on Agency, the one the client asked for, else the one the
    user last picked; otherwise the first. Starter has no switcher, so it never picks."""
    workspaces = open_workspaces(session, access.customer)
    by_id = {workspace.id: workspace for workspace in workspaces}
    if has_workspaces(access) and requested is not None:
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
    """When a customer's last user deletes their account, their company profiles and careers page audits go too.
    The billing records stay, as the privacy page says. Call after deleting the user, before committing."""
    if customer_id is None:
        return
    session.flush()
    users = session.exec(select(func.count()).select_from(User).where(User.customer_id == customer_id)).one()
    if users == 0:
        session.exec(delete(Audit).where(col(Audit.customer_id) == customer_id))
        session.exec(delete(Workspace).where(col(Workspace.customer_id) == customer_id))
