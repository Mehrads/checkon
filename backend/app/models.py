import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from pydantic import EmailStr
from sqlalchemy import JSON, Column, Text, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


# Properties to receive via API on update, all are optional
class UserUpdate(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None
    full_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(default_factory=get_datetime_utc)
    items: list[Item] = Relationship(back_populates="owner", cascade_delete=True)
    # The paying customer this user checks for; None for admins and anyone without a plan
    customer_id: uuid.UUID | None = Field(
        default=None, foreign_key="customer.id", ondelete="SET NULL", index=True
    )
    # The client workspace this user last picked (Agency); None means the customer's first
    workspace_id: uuid.UUID | None = Field(
        default=None, foreign_key="workspace.id", ondelete="SET NULL"
    )


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(default_factory=get_datetime_utc)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class LoginCode(SQLModel, table=True):
    """A sign-in code emailed after a correct password; the browser holds the matching challenge."""

    __tablename__ = "login_code"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=get_datetime_utc)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE", index=True
    )
    challenge_hash: str = Field(unique=True, max_length=64)  # SHA-256 of the challenge
    code_hash: str = Field(max_length=64)  # HMAC of the challenge and the code
    expires_at: datetime
    attempts: int = 0


class LoginChallenge(SQLModel):
    challenge: str


class LoginCodeIn(SQLModel):
    challenge: str = Field(max_length=64)
    code: str = Field(schema_extra={"pattern": r"^\d{6}$"})


# Free check (v1): usage, spend and research. Keys are HMACs, never raw IPs or cookies,
# and posting text is stored only when the person opts in (Technical Design §11).


class FreeCheckUse(SQLModel, table=True):
    __tablename__ = "free_check_use"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    key_hash: str = Field(index=True, max_length=64)  # HMAC of "cookie:<id>" or "ip:<address>"
    used_at: datetime = Field(default_factory=get_datetime_utc, index=True)


class FreeCheckSpend(SQLModel, table=True):
    __tablename__ = "free_check_spend"
    day: date = Field(primary_key=True)  # Toronto date
    usd: Decimal = Field(default=Decimal(0), max_digits=12, decimal_places=6)


class ResearchAnswer(SQLModel, table=True):
    __tablename__ = "research_answer"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=get_datetime_utc)
    check_id: str | None = Field(default=None, max_length=64)
    question_id: str = Field(max_length=64)
    answer: str = Field(max_length=255)


class CustomRequest(SQLModel, table=True):
    __tablename__ = "custom_request"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=get_datetime_utc)
    check_id: str | None = Field(default=None, max_length=64)
    hr_system: str = Field(max_length=255)
    postings_per_month: str = Field(max_length=64)
    wants: str = Field(max_length=2000)
    email: str = Field(max_length=255)


class Feedback(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=get_datetime_utc)
    check_id: str | None = Field(default=None, max_length=64)
    target_kind: str = Field(max_length=16)  # finding, patch or check
    target_id: str = Field(max_length=64)  # rule id, patch id, or "check"
    rating: str = Field(max_length=16)  # up, down or looks_wrong
    reason: str | None = Field(default=None, max_length=64)
    comment: str | None = Field(default=None, max_length=2000)
    versions: dict[str, str] = Field(default_factory=dict, sa_column=Column(JSON))
    posting_text: str | None = Field(default=None, sa_column=Column(Text))  # only with consent
    review_status: str = Field(default="new", max_length=16)


class ContactMessage(SQLModel, table=True):
    """A message from the site's contact form: plans, custom setups, questions."""

    __tablename__ = "contact_message"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=get_datetime_utc)
    name: str = Field(max_length=255)
    email: str = Field(max_length=255)
    company: str | None = Field(default=None, max_length=255)
    interest: str = Field(max_length=32)  # starter, agency, custom or other
    message: str = Field(max_length=2000)
    check_id: str | None = Field(default=None, max_length=64)


class UsageEvent(SQLModel, table=True):
    """One step of a check, free or on a plan (`plan`), for the success metrics (PRD §2). Never holds posting text; `visitor` is an
    HMAC of the anonymous cookie, kept (unlike the week-long quota keys) so returning visitors can be counted.
    """

    __tablename__ = "usage_event"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    at: datetime = Field(default_factory=get_datetime_utc, index=True)
    kind: str = Field(max_length=16, index=True)  # check, refused, quota, paused, failed, refine, answers, accept,
    # pay_suggest, pay_confirm
    check_id: str | None = Field(default=None, max_length=64, index=True)
    visitor: str | None = Field(default=None, max_length=64, index=True)
    status: str | None = Field(default=None, max_length=32)  # report status, refusal reason, or ok / failed
    duration_ms: int | None = None
    usd: Decimal | None = Field(default=None, max_digits=12, decimal_places=6)
    count: int | None = None  # fixes applied, on accept
    plan: str | None = Field(default=None, max_length=16)  # starter or agency for a paid check; None when free


# Paid plans (Stripe Billing). Card details stay with Stripe; we keep the ids and the subscription's state.


class Customer(SQLModel, table=True):
    """One Stripe customer and its subscription. Its users share the plan's checks for the billing period."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=get_datetime_utc)
    stripe_customer_id: str = Field(unique=True, max_length=255)
    email: str | None = Field(default=None, max_length=255)  # the email given at Checkout
    stripe_subscription_id: str | None = Field(default=None, max_length=255)
    plan: str | None = Field(default=None, max_length=16)  # starter or agency
    subscription_status: str | None = Field(default=None, max_length=32)  # Stripe's: active, past_due, canceled…
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False


class PaidCheck(SQLModel, table=True):
    """A check that counted against a plan: the allowance and the customer's history. Never the posting text."""

    __tablename__ = "paid_check"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=get_datetime_utc, index=True)
    customer_id: uuid.UUID = Field(foreign_key="customer.id", nullable=False, ondelete="CASCADE", index=True)
    user_id: uuid.UUID | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL")
    check_id: str = Field(max_length=64, index=True)
    title: str | None = Field(default=None, max_length=255)  # the job title, as written in the posting
    status: str = Field(max_length=32)  # the report status when checked
    final_status: str | None = Field(default=None, max_length=32)  # after the fixes were applied
    extra: bool = False  # past the plan's checks for the period, so billed at the extra-check price
    reported_at: datetime | None = None  # when an extra check was sent to Stripe's meter
    workspace_id: uuid.UUID | None = Field(default=None, foreign_key="workspace.id", ondelete="SET NULL", index=True)


class Workspace(SQLModel, table=True):
    """The company a customer checks postings for, and its company profile (PRD FR2): facts every check starts
    from, so the check doesn't ask or search for them. Starter has one; Agency has one per client (FR10), and
    the plan's checks are shared by all of them. Company facts only, never posting text. None means not given,
    and the check asks or searches as it does without a profile.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=get_datetime_utc)
    customer_id: uuid.UUID = Field(foreign_key="customer.id", nullable=False, ondelete="CASCADE", index=True)
    name: str | None = Field(default=None, max_length=255)  # the client's name in the switcher; None: the employer's
    archived_at: datetime | None = None  # hidden from the switcher; its checks keep the tag
    employer_name: str | None = Field(default=None, max_length=255)  # searched for the headcount when none is given
    # Employees in Ontario on the day of posting, part-time, casual and on leave included
    headcount: int | None = None
    meets_headcount_threshold: bool | None = None  # "25 or more" without an exact figure; None when headcount is set
    uses_ai_in_hiring: bool | None = None  # AI screens, assesses or selects applicants, by them or a recruiter
    wording: str = Field(default="formal", max_length=16)  # the wording library's variant: formal or plain
    updated_at: datetime | None = None  # when the profile was last saved


class StripeEvent(SQLModel, table=True):
    """Webhook events already processed, so a redelivered event changes nothing."""

    __tablename__ = "stripe_event"
    id: str = Field(primary_key=True, max_length=255)
    type: str = Field(max_length=64)
    received_at: datetime = Field(default_factory=get_datetime_utc)


class EmployerSizeSearch(SQLModel, table=True):
    """An employer-size web search (app/compliance/employer.py), kept 30 days so restarts and deploys don't
    repeat it. Keyed by the employer's name and the job location; no posting text is stored.
    """

    __tablename__ = "employer_size_search"
    employer: str = Field(primary_key=True, max_length=255)  # lower-cased, spaces collapsed
    location: str = Field(primary_key=True, max_length=255)  # lower-cased; "" when the posting names none
    size: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))  # an EmployerSize
    searched_at: datetime = Field(default_factory=get_datetime_utc, index=True)


class PayBand(SQLModel, table=True):
    """A pay range the customer confirmed for a job title (PRD FR9), kept with the company profile or client
    workspace the check used: the next pay suggestion for that title starts from it. Never posting text.
    """

    __tablename__ = "pay_band"
    __table_args__ = (UniqueConstraint("workspace_id", "role"),)
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspace.id", nullable=False, ondelete="CASCADE", index=True)
    role: str = Field(max_length=255)  # the job title, lower-cased without punctuation (app/pay/suggest.py)
    title: str = Field(max_length=255)  # the job title as the posting writes it
    noc_code: str | None = Field(default=None, max_length=5)  # the occupation the suggestion used, if any
    min: Decimal = Field(max_digits=12, decimal_places=2)
    max: Decimal = Field(max_digits=12, decimal_places=2)
    unit: str = Field(max_length=8)  # hour, week, month or year
    confirmed_at: datetime = Field(default_factory=get_datetime_utc)
    confirmed_by: uuid.UUID | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL")


class PayPostingSearch(SQLModel, table=True):
    """A web search for the pay in current postings (app/pay/suggest.py), kept a week so repeat suggestions
    don't search again. Keyed by job title and place; holds quoted pay and links, never posting text.
    """

    __tablename__ = "pay_posting_search"
    title: str = Field(primary_key=True, max_length=255)  # lower-cased, without punctuation
    location: str = Field(primary_key=True, max_length=255)  # as the employer-size cache keys it
    result: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))  # a PostingSearch
    searched_at: datetime = Field(default_factory=get_datetime_utc, index=True)


class Audit(SQLModel, table=True):
    """A careers page audit (PRD FR13): the open Ontario postings on a customer's job board or careers page, each
    checked against the plan for one workspace. The page's address and each posting's title, place, link and
    result; never the posting text.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=get_datetime_utc, index=True)
    customer_id: uuid.UUID = Field(foreign_key="customer.id", nullable=False, ondelete="CASCADE", index=True)
    workspace_id: uuid.UUID | None = Field(default=None, foreign_key="workspace.id", ondelete="SET NULL", index=True)
    user_id: uuid.UUID | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL")
    url: str = Field(max_length=2048)  # the address the customer entered
    source: str = Field(max_length=16)  # greenhouse, lever, ashby, smartrecruiters, or page (a careers page)
    board: str = Field(max_length=2048)  # the board's name at the ATS; for a careers page, the page read
    board_name: str | None = Field(default=None, max_length=255)  # the company's name, when the board gives it
    found: int  # open postings on the board, anywhere
    outside_ontario: int  # of those, the ones for work elsewhere, left out


class AuditPosting(SQLModel, table=True):
    """One posting in an audit: what the board lists publicly, and the check's result. Never the posting text."""

    __tablename__ = "audit_posting"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    audit_id: uuid.UUID = Field(foreign_key="audit.id", nullable=False, ondelete="CASCADE", index=True)
    position: int  # order in the report
    external_id: str = Field(max_length=2048)  # the board's id for the posting; a careers page's: its address
    title: str = Field(max_length=255)
    location: str | None = Field(default=None, max_length=255)
    url: str = Field(max_length=2048)  # the posting's public page
    where: str = Field(max_length=16)  # ontario, or canada (Canada-wide, which may be filled in Ontario)
    status: str = Field(default="queued", max_length=32)  # queued, checking, a report status, refused or failed
    issues: list[dict[str, str]] = Field(default_factory=list, sa_column=Column(JSON))  # [{rule, verdict}] to act on
    note: str | None = Field(default=None, max_length=255)  # why it wasn't checked
    check_id: str | None = Field(default=None, max_length=64)  # the full check, in memory for an hour
    checked_at: datetime | None = None  # when the check started (status checking) or finished
