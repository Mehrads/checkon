"""Limits on the free check (04-V1-Scope.md, section 4): Turnstile, a weekly quota per cookie and per IP,
a per-IP rate limit, an origin check and a daily spend cap. Every limit is enforced on the server.
"""

import hashlib
import hmac
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Protocol

import httpx
from fastapi import HTTPException, Request, Response
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, col, delete, select

from app.core.config import settings
from app.models import FreeCheckSpend, FreeCheckUse, get_datetime_utc

COOKIE = "free_check_id"
WEEK = timedelta(days=7)
TURNSTILE_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def refused(status: int, reason: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"reason": reason, "message": message})


# Who is asking


def client_ip(request: Request) -> str:
    # Behind Cloud Run, the server must trust the proxy's X-Forwarded-For (uvicorn --forwarded-allow-ips).
    return request.client.host if request.client else "unknown"


def visitor_cookie(request: Request, response: Response) -> str:
    """The anonymous visitor id, set or refreshed on the response; it carries nothing else."""
    value = request.cookies.get(COOKIE) or secrets.token_urlsafe(16)
    response.set_cookie(
        COOKIE, value, max_age=365 * 24 * 3600, httponly=True, samesite="lax",
        secure=settings.FASTAPI_ENV != "development",
    )  # fmt: skip
    return value


def same_origin(request: Request) -> None:
    """Browsers send Origin on POST; refuse other sites' pages. Turnstile is the real guard against scripts."""
    origin = request.headers.get("origin")
    if origin is None:
        return
    allowed = {settings.FRONTEND_HOST.rstrip("/"), str(request.base_url).rstrip("/")}
    if origin.rstrip("/") not in allowed:
        raise refused(403, "origin", "Requests must come from the checker's own page.")


class RateLimiter:
    """Requests per IP per minute, in this process (v1 runs one instance)."""

    def __init__(self, per_minute: int) -> None:
        self.per_minute = per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] < now - 60:
                hits.popleft()
            if len(hits) >= self.per_minute:
                return False
            hits.append(now)
            return True


_limiter = RateLimiter(settings.FREE_CHECK_REQUESTS_PER_MINUTE)


def rate_limited(request: Request) -> None:
    if not _limiter.allow(client_ip(request)):
        raise refused(429, "rate_limit", "Too many requests. Wait a minute and try again.")


# Turnstile (Cloudflare's invisible CAPTCHA)


class Verifier(Protocol):
    def verify(self, token: str | None, ip: str) -> bool: ...


class TurnstileVerifier:
    def __init__(self, secret: str | None, required: bool) -> None:
        self.secret = secret
        self.required = required

    def verify(self, token: str | None, ip: str) -> bool:
        if not self.secret:
            if self.required:
                raise refused(503, "not_configured", "The checker isn't configured: TURNSTILE_SECRET_KEY is not set.")
            return True  # development without Turnstile
        if not token:
            return False
        try:
            reply = httpx.post(TURNSTILE_URL, data={"secret": self.secret, "response": token, "remoteip": ip}, timeout=5)
            return reply.json().get("success") is True
        except (httpx.HTTPError, ValueError):
            return False


# Quota and spend


class Limits(Protocol):
    def next_free_check(self, cookie: str, ip: str) -> datetime | None: ...
    def record_use(self, cookie: str, ip: str) -> None: ...
    def budget_left(self) -> bool: ...
    def add_spend(self, usd: Decimal) -> None: ...


class PostgresLimits:
    """Weekly quota per cookie and per IP, and the day's spend, in Postgres. Keys are HMACs, not raw values."""

    def __init__(self, session: Session, today: date, per_week: int, daily_cap: Decimal, secret: str) -> None:
        self.session = session
        self.today = today
        self.per_week = per_week
        self.daily_cap = daily_cap
        self.secret = secret.encode()

    def _keys(self, cookie: str, ip: str) -> list[str]:
        return [hmac.new(self.secret, f"{kind}:{value}".encode(), hashlib.sha256).hexdigest()
                for kind, value in (("cookie", cookie), ("ip", ip))]  # fmt: skip

    def next_free_check(self, cookie: str, ip: str) -> datetime | None:
        since = get_datetime_utc() - WEEK
        rows = self.session.exec(
            select(FreeCheckUse).where(col(FreeCheckUse.key_hash).in_(self._keys(cookie, ip)), FreeCheckUse.used_at > since)
        ).all()
        by_key: dict[str, list[datetime]] = defaultdict(list)
        for row in rows:
            by_key[row.key_hash].append(row.used_at)
        blocked = [sorted(times) for times in by_key.values() if len(times) >= self.per_week]
        return min(times[-self.per_week] for times in blocked) + WEEK if blocked else None

    def record_use(self, cookie: str, ip: str) -> None:
        now = get_datetime_utc()
        self.session.exec(delete(FreeCheckUse).where(FreeCheckUse.used_at < now - WEEK - timedelta(days=1)))
        for key in self._keys(cookie, ip):
            self.session.add(FreeCheckUse(key_hash=key, used_at=now))
        self.session.commit()

    def budget_left(self) -> bool:
        spend = self.session.get(FreeCheckSpend, self.today)
        return spend is None or spend.usd < self.daily_cap

    def add_spend(self, usd: Decimal) -> None:
        if usd <= 0:
            return
        upsert = insert(FreeCheckSpend).values(day=self.today, usd=usd)
        upsert = upsert.on_conflict_do_update(index_elements=["day"], set_={"usd": FreeCheckSpend.usd + usd})
        self.session.exec(upsert)
        self.session.commit()
