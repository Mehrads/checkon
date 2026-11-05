"""Usage events for the usage stats: one row per step of a check, with its timing and model
cost, and the plan for a paid check. No posting text is stored, and the visitor is an HMAC of the anonymous
cookie.
"""

import hashlib
import hmac
import time
from decimal import Decimal
from typing import Protocol

from sqlmodel import Session

from app.core.config import settings
from app.core.tracing import RequestTrace
from app.models import UsageEvent


def visitor_hash(cookie: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"visitor:{cookie}".encode(), hashlib.sha256).hexdigest()


def elapsed_ms(started: float) -> int:
    """Milliseconds since a `time.monotonic()` reading."""
    return round((time.monotonic() - started) * 1000)


class Usage(Protocol):
    def record(
        self, kind: str, *, check_id: str | None = None, visitor: str | None = None, status: str | None = None,
        duration_ms: int | None = None, usd: Decimal | None = None, count: int | None = None, plan: str | None = None,
    ) -> None: ...  # fmt: skip


class PostgresUsage:
    """Also notes each event on the request's trace, without the visitor."""

    def __init__(self, session: Session, trace: RequestTrace | None = None) -> None:
        self.session = session
        self.trace = trace

    def record(
        self, kind: str, *, check_id: str | None = None, visitor: str | None = None, status: str | None = None,
        duration_ms: int | None = None, usd: Decimal | None = None, count: int | None = None, plan: str | None = None,
    ) -> None:  # fmt: skip
        if self.trace is not None:
            self.trace.note(
                kind=kind, check_id=check_id, status=status, duration_ms=duration_ms,
                usd=float(usd) if usd is not None else None, count=count, plan=plan,
            )  # fmt: skip
        self.session.add(UsageEvent(
            kind=kind, check_id=check_id, visitor=visitor, status=status, duration_ms=duration_ms, usd=usd, count=count,
            plan=plan,
        ))  # fmt: skip
        self.session.commit()
