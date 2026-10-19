import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from pydantic import EmailStr
from sqlalchemy import JSON, Column, Text
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


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


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
