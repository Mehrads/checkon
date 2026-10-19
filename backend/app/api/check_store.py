"""Server-side state for one free check, held in memory and kept for an hour.

The posting text lives only here, never in the database (Technical Design §11, anonymous checks).
v1 runs one process; quotas and a shared store move to Postgres in step 6.
"""

import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import date

from app.compliance.inspector import Inspection, SentenceLabels
from app.compliance.models import Context
from app.compliance.refiner import Refinement


@dataclass
class CheckState:
    posting_date: date
    ctx: Context
    inspection: Inspection
    refinement: Refinement | None = None
    label_cache: dict[str, SentenceLabels] = field(default_factory=dict)
    rewrites: dict[str, str] = field(default_factory=dict)
    id: str = field(default_factory=lambda: secrets.token_urlsafe(16))
    created: float = field(default_factory=time.monotonic)


class CheckStore:
    def __init__(self, ttl_seconds: float = 3600, max_checks: int = 1000) -> None:
        self.ttl = ttl_seconds
        self.max_checks = max_checks
        self._checks: dict[str, CheckState] = {}
        self._lock = threading.Lock()

    def add(self, state: CheckState) -> CheckState:
        with self._lock:
            self._expire()
            while len(self._checks) >= self.max_checks:
                self._checks.pop(next(iter(self._checks)))  # oldest first
            self._checks[state.id] = state
        return state

    def get(self, check_id: str) -> CheckState | None:
        with self._lock:
            self._expire()
            return self._checks.get(check_id)

    def _expire(self) -> None:
        cutoff = time.monotonic() - self.ttl
        for check_id in [i for i, state in self._checks.items() if state.created < cutoff]:
            del self._checks[check_id]
