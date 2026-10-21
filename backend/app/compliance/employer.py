"""Employer size from a web search, for the applicability gate (ON-APPL-01) in the free check.

The person is never asked. The rules apply unless the search clearly shows fewer employees than the
threshold; when the employer isn't named or nothing is found, the rules are assumed to apply.
The search only reports figures; code decides, using the threshold from the rule pack.
"""

import re
import unicodedata
from decimal import Decimal
from typing import Any, Literal, Protocol
from urllib.parse import urlsplit

from pydantic import BaseModel

from app.compliance.extraction import PROMPTS_DIR
from app.compliance.llm import LLMError, ModelSettings, StructuredLLM

CACHE_SECONDS = 30 * 24 * 3600
MAX_SEARCHES = 3

_ASIDES = re.compile(r"\([^)]*\)|\[[^\]]*\]")  # "(hybrid)", "[remote]"
_WORK_MODES = re.compile(r"\b(?:hybrid|remote|on-?site|in[- ]office|in[- ]person)\b")
_PLACE_WORDS = {"ontario": "on", "canada": ""}


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


class SizeCache(Protocol):
    """Searches by employer and location, kept for 30 days (Postgres in the app: app/api/employer_cache.py)."""

    def get(self, key: tuple[str, str]) -> EmployerSize | None: ...
    def put(self, key: tuple[str, str], value: EmployerSize) -> None: ...


def place_key(location: str | None) -> str:
    """The job location as a cache key, so that "Ottawa, ON (hybrid)", "Ottawa, Ontario, Canada" and "ottawa on"
    share one search. Work arrangements, punctuation and accents don't change an employer's size.
    """
    text = unicodedata.normalize("NFKD", (location or "").lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    words = re.sub(r"\W+", " ", _WORK_MODES.sub(" ", _ASIDES.sub(" ", text))).split()
    return " ".join(word for word in (_PLACE_WORDS.get(word, word) for word in words) if word)


def look_up(
    employer: str, location: str | None, llm: StructuredLLM, settings: ModelSettings, cache: SizeCache | None = None
) -> EmployerSize | None:
    """None when the search fails; the caller then assumes the rules apply. Without a cache, every call searches."""
    key = (" ".join(employer.lower().split()), place_key(location))
    if cache is not None and (cached := cache.get(key)) is not None:
        return cached
    user = f"<employer>{employer}</employer>"
    if location:
        user += f"\n<job_location>{location}</job_location>"
    system = (PROMPTS_DIR / "employer_size.md").read_text(encoding="utf-8")
    try:
        size = llm.parse(system=system, user=user, schema=EmployerSize, settings=settings, tools=[search_tool()])
    except LLMError:
        return None
    if cache is not None:
        cache.put(key, size)
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
