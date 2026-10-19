"""Employer size from a web search, for the applicability gate (ON-APPL-01) in the free check.

The person is never asked. The rules apply unless the search clearly shows fewer employees than the
threshold; when the employer isn't named or nothing is found, the rules are assumed to apply.
The search only reports figures; code decides, using the threshold from the rule pack.
"""

import threading
import time
from decimal import Decimal
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel

from app.compliance.extraction import PROMPTS_DIR
from app.compliance.llm import LLMError, ModelSettings, StructuredLLM

CACHE_SECONDS = 30 * 24 * 3600
MAX_SEARCHES = 3


class EmployerSize(BaseModel):
    found: bool
    total_employees_min: int | None
    total_employees_max: int | None
    ontario_employees_min: int | None
    ontario_employees_max: int | None
    summary: str
    source_url: str | None


class SizeDecision(BaseModel):
    meets_threshold: bool
    basis: Literal["search", "assumed"]
    evidence: str | None = None  # "Acme Corp: about 2,000 employees worldwide (acme.com)"


def search_tool() -> dict[str, Any]:
    return {
        "type": "web_search_20250305",
        "name": "web_search",
        "max_uses": MAX_SEARCHES,
        "user_location": {"type": "approximate", "country": "CA", "region": "Ontario"},
    }


class _Cache:
    """Lookups by employer and location, kept for 30 days in this process."""

    def __init__(self) -> None:
        self._items: dict[tuple[str, str], tuple[float, EmployerSize]] = {}
        self._lock = threading.Lock()

    def get(self, key: tuple[str, str]) -> EmployerSize | None:
        with self._lock:
            item = self._items.get(key)
            if item and time.monotonic() - item[0] < CACHE_SECONDS:
                return item[1]
            return None

    def put(self, key: tuple[str, str], value: EmployerSize) -> None:
        with self._lock:
            if len(self._items) >= 5000:
                self._items.pop(next(iter(self._items)))
            self._items[key] = (time.monotonic(), value)


CACHE = _Cache()


def look_up(employer: str, location: str | None, llm: StructuredLLM, settings: ModelSettings) -> EmployerSize | None:
    """None when the search fails; the caller then assumes the rules apply."""
    key = (" ".join(employer.lower().split()), (location or "").lower())
    if (cached := CACHE.get(key)) is not None:
        return cached
    user = f"<employer>{employer}</employer>"
    if location:
        user += f"\n<job_location>{location}</job_location>"
    system = (PROMPTS_DIR / "employer_size.md").read_text(encoding="utf-8")
    try:
        size = llm.parse(system=system, user=user, schema=EmployerSize, settings=settings, tools=[search_tool()])
    except LLMError:
        return None
    CACHE.put(key, size)
    return size


def decide(employer: str | None, size: EmployerSize | None, threshold: Decimal) -> SizeDecision:
    if employer is None or size is None or not size.found:
        return SizeDecision(meets_threshold=True, basis="assumed")
    source = urlsplit(size.source_url).netloc.removeprefix("www.") if size.source_url else ""
    evidence = f"{employer}: {size.summary}" + (f" ({source})" if source else "")
    below = [n for n in (size.ontario_employees_max, size.total_employees_max) if n is not None and n < threshold]
    if below:
        return SizeDecision(meets_threshold=False, basis="search", evidence=evidence)
    known = [n for n in (size.ontario_employees_min, size.total_employees_min) if n is not None]
    if any(n >= threshold for n in known):
        return SizeDecision(meets_threshold=True, basis="search", evidence=evidence)
    return SizeDecision(meets_threshold=True, basis="assumed")  # figures straddle the threshold or are missing
