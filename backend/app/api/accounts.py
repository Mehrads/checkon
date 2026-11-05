"""Accounts: the signed-in users who share company profiles (workspaces), check history, careers page audits, pay
ranges and the archive. Every signed-in user belongs to one, made the first time they need it.

There are no plans and nothing is billed: whoever runs the server pays the model fees. Two settings keep that in
hand: SIGNUP_OPEN (whether anyone can make an account, or only an admin can add users) and
ACCOUNT_CHECKS_PER_30_DAYS (each account's checks in any 30 days; 0 means no limit). Visitors who aren't signed in
get the free check's own limits (app/api/free_check.py).

The database table is still called `customer`, and a signed-in check is a `PaidCheck` row, from the hosted
service this code came from.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlmodel import Session, col, func, select

from app.core.config import settings
from app.models import Customer, PaidCheck, User, get_datetime_utc

# What a signed-in check records in UsageEvent.plan and CheckState.plan; None there means a visitor's free check.
ACCOUNT = "account"
WINDOW = timedelta(days=30)


@dataclass(frozen=True)
class Access:
    """A signed-in user and their account."""

    user: User
    customer: Customer


def account_for(session: Session, user: User) -> Customer:
    """The user's account, made on first use. The user row is locked so two requests at once make only one."""
    if user.customer_id is not None and (customer := session.get(Customer, user.customer_id)) is not None:
        return customer
    locked = session.exec(select(User).where(User.id == user.id).with_for_update()).one()
    if locked.customer_id is not None and (customer := session.get(Customer, locked.customer_id)) is not None:
        return customer
    customer = Customer(email=user.email)
    session.add(customer)
    session.flush()
    locked.customer_id = customer.id
    session.add(locked)
    session.commit()
    session.refresh(customer)
    session.refresh(user)
    return customer


def access_for(session: Session, user: User | None) -> Access | None:
    """None for a visitor: they get the free check."""
    if user is None:
        return None
    return Access(user, account_for(session, user))


def checks_used(session: Session, customer_id: uuid.UUID, now: datetime) -> int:
    """The account's checks in the last 30 days."""
    return session.exec(
        select(func.count()).select_from(PaidCheck).where(
            PaidCheck.customer_id == customer_id, PaidCheck.created_at > now - WINDOW
        )
    ).one()  # fmt: skip


def checks_left(session: Session, customer_id: uuid.UUID, now: datetime) -> int | None:
    """None when accounts have no limit."""
    limit = settings.ACCOUNT_CHECKS_PER_30_DAYS
    return None if limit <= 0 else max(limit - checks_used(session, customer_id, now), 0)


class AccountChecks:
    """One signed-in account's checks: the optional limit, and the history (date, job title, result; never the
    posting text, which only the archive keeps, when a workspace turns it on)."""

    def __init__(self, session: Session, access: Access) -> None:
        self.session = session
        self.access = access

    @property
    def customer_id(self) -> uuid.UUID:
        return self.access.customer.id

    def next_check(self) -> datetime | None:
        """When the account can check again, if it has used its checks for the last 30 days."""
        limit = settings.ACCOUNT_CHECKS_PER_30_DAYS
        if limit <= 0:
            return None
        now = get_datetime_utc()
        recent = self.session.exec(
            select(PaidCheck.created_at)
            .where(PaidCheck.customer_id == self.customer_id, PaidCheck.created_at > now - WINDOW)
            .order_by(col(PaidCheck.created_at).desc())
            .limit(limit)
        ).all()
        return recent[-1] + WINDOW if len(recent) >= limit else None

    def record(self, check_id: str, title: str | None, status: str, workspace_id: uuid.UUID | None = None) -> PaidCheck:
        check = PaidCheck(
            created_at=get_datetime_utc(), customer_id=self.customer_id, user_id=self.access.user.id,
            check_id=check_id, title=title[:255] if title else None, status=status, workspace_id=workspace_id,
        )  # fmt: skip
        self.session.add(check)
        self.session.commit()
        self.session.refresh(check)
        return check


def record_final_status(session: Session, check_id: str, status: str) -> None:
    check = session.exec(select(PaidCheck).where(PaidCheck.check_id == check_id)).first()
    if check is not None:
        check.final_status = status
        session.add(check)
        session.commit()
