"""Usage events for the success metrics (PRD §2): one row per step of a free check, with its timing and
model cost. No posting text is stored, and the visitor is an HMAC of the anonymous cookie.
"""

import hashlib
import hmac
import time
from decimal import Decimal
from typing import Protocol

from sqlmodel import Session

from app.core.config import settings
from app.models import UsageEvent


def visitor_hash(cookie: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"visitor:{cookie}".encode(), hashlib.sha256).hexdigest()


def elapsed_ms(started: float) -> int:
    """Milliseconds since a `time.monotonic()` reading."""
    return round((time.monotonic() - started) * 1000)


class Usage(Protocol):
    def record(
        self, kind: str, *, check_id: str | None = None, visitor: str | None = None, status: str | None = None,
        duration_ms: int | None = None, usd: Decimal | None = None, count: int | None = None,
    ) -> None: ...  # fmt: skip


class PostgresUsage:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self, kind: str, *, check_id: str | None = None, visitor: str | None = None, status: str | None = None,
        duration_ms: int | None = None, usd: Decimal | None = None, count: int | None = None,
    ) -> None:  # fmt: skip
        self.session.add(UsageEvent(
            kind=kind, check_id=check_id, visitor=visitor, status=status, duration_ms=duration_ms, usd=usd, count=count,
        ))  # fmt: skip
        self.session.commit()
