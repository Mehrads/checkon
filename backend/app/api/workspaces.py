"""Company profiles (PRD FR2): the facts a paying customer's checks start from, so a check doesn't ask for them
or search for the employer's size. Each customer has one, created empty on first use. Company facts only:
the posting text is never stored.
"""

import uuid
from typing import Literal

from sqlmodel import Session, col, delete, func, select

from app.compliance.models import Context
from app.models import Customer, User, Workspace

Wording = Literal["formal", "plain"]


def current_workspace(session: Session, customer: Customer) -> Workspace:
    """The customer's profile. The customer row is locked before creating one, so two requests at once can't
    both create it."""
    mine = select(Workspace).where(Workspace.customer_id == customer.id).order_by(col(Workspace.created_at))
    if (found := session.exec(mine).first()) is not None:
        return found
    session.exec(select(Customer).where(Customer.id == customer.id).with_for_update()).one()
    if (found := session.exec(mine).first()) is None:
        found = Workspace(customer_id=customer.id)
        session.add(found)
    session.commit()
    session.refresh(found)
    return found


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
    """When a customer's last user deletes their account, their company profiles go too. The billing records
    stay, as the privacy page says. Call after deleting the user, before committing."""
    if customer_id is None:
        return
    session.flush()
    users = session.exec(select(func.count()).select_from(User).where(User.customer_id == customer_id)).one()
    if users == 0:
        session.exec(delete(Workspace).where(col(Workspace.customer_id) == customer_id))
