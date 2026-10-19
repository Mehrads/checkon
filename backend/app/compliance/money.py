"""Deterministic pay parser: the second reading of pay, independent of the LLM (Technical Design §4, step 4).

It reads only amounts with a currency marker ($, C$, US$, CAD, USD or "dollars"). Pay written without
one is left to the LLM; the two readings then disagree and the user is asked, which is the safe side.
"""

import re
from dataclasses import dataclass
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.compliance.models import PayUnit, Span

_AMOUNT = re.compile(
    r"""
    (?<![\w.,$])
    (?P<pre>(?:US|CA|CDN|C)\$\s?|\$\s?|(?:CAD|USD|CDN)\s?)?
    (?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)
    (?P<k>\s?[kK](?![A-Za-z]))?
    (?P<post>\s?\$|\s?(?:CAD|USD|CDN|dollars)\b)?
    (?!\d)(?!,\d)
    (?!\s?(?:[mMbB]\b|million|billion|mm\b))
    """,
    re.VERBOSE,
)
_UNIT_WORD = r"(?:hours?|hrs?|h|years?|yrs?|annum|months?|mos?|weeks?|wks?)"
_RANGE_SEP = re.compile(
    rf"\s*(?:(?:/\s*|per\s+|an?\s+){_UNIT_WORD}\s*)?(?:[-–—]|(?P<word>to|and))\s*", re.IGNORECASE
)
_RANGE_PRE = re.compile(r"\b(?:between|from)\s*$", re.IGNORECASE)
_BETWEEN = re.compile(r"\bbetween\s*$", re.IGNORECASE)
_UP_TO = re.compile(r"\b(?:up\s+to|upto|max(?:imum)?(?:\s+of)?|not\s+to\s+exceed)\s*:?\s*$", re.IGNORECASE)
_MIN_PRE = re.compile(
    r"\b(?:starting\s+(?:at|from)|starts?\s+at|from|min(?:imum)?(?:\s+of)?|at\s+least|no\s+less\s+than)\s*:?\s*$",
    re.IGNORECASE,
)
_EXTRAS = r"(?:bonus(?:es)?|commissions?|benefits|equity|stock|overtime|ot|tips|vacation|incentives?|shares|rrsp|pension)"
_PLUS = re.compile(rf"\s?\+(?!\s*{_EXTRAS}\b)", re.IGNORECASE)
_AND_UP = re.compile(r"\s+(?:and\s+(?:up|above|higher)|or\s+(?:more|higher|above))\b", re.IGNORECASE)
_PERIOD_AFTER = re.compile(
    r"\s*(?:\(?(?:CAD|USD)\)?\s*)?"
    rf"(?:(?:/\s*|per\s+|an?\s+|each\s+|p/\s*)(?P<unit>{_UNIT_WORD})\b"
    r"|(?P<adverb>hourly|annually|yearly|annual|monthly|weekly)\b)",
    re.IGNORECASE,
)
# Period words before the amount, e.g. "Hourly rate: $25". "40 hours per week" deliberately doesn't count.
_PERIOD_BEFORE = re.compile(
    r"\b(?:(?P<hour>hourly|hour\s+rate)|(?P<week>weekly)|(?P<month>monthly)"
    r"|(?P<year>annual(?:ly|ized)?|yearly|per\s+annum|salary|salaried))\b",
    re.IGNORECASE,
)
_UNITS = {
    "h": PayUnit.HOUR, "hr": PayUnit.HOUR, "hrs": PayUnit.HOUR, "hour": PayUnit.HOUR, "hours": PayUnit.HOUR,
    "hourly": PayUnit.HOUR,
    "wk": PayUnit.WEEK, "wks": PayUnit.WEEK, "week": PayUnit.WEEK, "weeks": PayUnit.WEEK, "weekly": PayUnit.WEEK,
    "mo": PayUnit.MONTH, "mos": PayUnit.MONTH, "month": PayUnit.MONTH, "months": PayUnit.MONTH,
    "monthly": PayUnit.MONTH,
    "yr": PayUnit.YEAR, "yrs": PayUnit.YEAR, "year": PayUnit.YEAR, "years": PayUnit.YEAR, "annum": PayUnit.YEAR,
    "annual": PayUnit.YEAR, "annually": PayUnit.YEAR, "yearly": PayUnit.YEAR,
}  # fmt: skip
# With no period in the text: below $300 reads as hourly, from $15,000 as yearly; in between stays unknown.
_HOURLY_BELOW = Decimal(300)
_YEARLY_FROM = Decimal(15000)
_BEFORE_WINDOW = 60
_AFTER_WINDOW = 40


_PER_UNIT = {PayUnit.HOUR: "an hour", PayUnit.WEEK: "a week", PayUnit.MONTH: "a month", PayUnit.YEAR: "a year"}


def _money(amount: Decimal) -> str:
    return f"${amount:,.0f}" if amount == amount.to_integral_value() else f"${amount:,.2f}"


def format_pay(low: Decimal | None, high: Decimal | None, unit: PayUnit | None) -> str:
    """Pay as a reader would write it: "$28–$34 an hour", "$70,000+ a year", "up to $90,000 a year"."""
    per = _PER_UNIT[unit] if unit else "(period not stated)"
    if low is not None and high is not None:
        amount = _money(low) if low == high else f"{_money(low)}–{_money(high)}"
    elif low is not None:
        amount = f"{_money(low)}+"
    else:
        amount = f"up to {_money(high)}"
    return f"{amount} {per}"


class PayReading(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    min: Decimal | None
    max: Decimal | None
    unit: PayUnit | None
    unit_stated: bool
    currency: str
    span: Span
    text: str


@dataclass(frozen=True)
class _Token:
    start: int
    end: int
    value: Decimal
    k: bool
    currency: str | None


def _token(match: re.Match[str]) -> _Token:
    marker = (match.group("pre") or "") + (match.group("post") or "")
    currency = None
    if marker.strip():
        currency = "USD" if "US" in marker else "CAD"
    value = Decimal(match.group("num").replace(",", ""))
    k = match.group("k") is not None
    return _Token(match.start(), match.end(), value * 1000 if k else value, k, currency)


def _before(text: str, start: int) -> tuple[int, str]:
    window_start = max(text.rfind("\n", 0, start) + 1, start - _BEFORE_WINDOW)
    return window_start, text[window_start:start]


def _after(text: str, end: int) -> str:
    line_end = text.find("\n", end)
    return text[end : min(len(text) if line_end < 0 else line_end, end + _AFTER_WINDOW)]


def _as_range(text: str, a: _Token, b: _Token) -> tuple[Decimal, Decimal] | None:
    separator = _RANGE_SEP.fullmatch(text[a.end : b.start])
    if not separator:
        return None
    if (separator.group("word") or "").lower() == "and" and not _BETWEEN.search(_before(text, a.start)[1]):
        return None
    low, high = a.value, b.value
    if b.k and not a.k and low * 1000 <= high:  # "$60-80k"
        low *= 1000
    if a.k and not b.k and high < low <= high * 1000:  # "$60k-80"
        high *= 1000
    return (low, high) if low <= high else None


def _period(text: str, start: int, end: int, top: Decimal) -> tuple[PayUnit | None, bool, int]:
    """Unit, whether the text states it, and the new end of the span."""
    after = _PERIOD_AFTER.match(_after(text, end))
    if after:
        word = (after.group("unit") or after.group("adverb")).lower()
        return _UNITS[word], True, end + after.end()
    found = [match for match in _PERIOD_BEFORE.finditer(_before(text, start)[1])]
    explicit = [match for match in found if not match.group("year")]
    if explicit or found:
        match = (explicit or found)[-1]
        unit = next(PayUnit(name) for name in ("hour", "week", "month", "year") if match.group(name))
        return unit, True, end
    if top < _HOURLY_BELOW:
        return PayUnit.HOUR, False, end
    if top >= _YEARLY_FROM:
        return PayUnit.YEAR, False, end
    return None, False, end


def _reading(
    text: str, start: int, end: int, low: Decimal | None, high: Decimal | None, currency: str
) -> PayReading:
    top = high if high is not None else low
    unit, stated, end = _period(text, start, end, top)
    return PayReading(
        min=low, max=high, unit=unit, unit_stated=stated, currency=currency, span=(start, end), text=text[start:end]
    )


def _range(text: str, a: _Token, b: _Token, low: Decimal, high: Decimal) -> PayReading:
    start = a.start
    window_start, before = _before(text, a.start)
    if prefix := _RANGE_PRE.search(before):
        start = window_start + prefix.start()
    return _reading(text, start, b.end, low, high, a.currency or b.currency or "CAD")


def _single(text: str, token: _Token) -> PayReading:
    start, end = token.start, token.end
    low: Decimal | None = token.value
    high: Decimal | None = token.value
    window_start, before = _before(text, start)
    after = _after(text, end)
    if up_to := _UP_TO.search(before):
        low, start = None, window_start + up_to.start()
    elif minimum := _MIN_PRE.search(before):
        high, start = None, window_start + minimum.start()
    elif open_end := (_PLUS.match(after) or _AND_UP.match(after)):
        high, end = None, end + open_end.end()
    return _reading(text, start, end, low, high, token.currency or "CAD")


def parse_pay(text: str) -> list[PayReading]:
    tokens = [_token(match) for match in _AMOUNT.finditer(text)]
    readings: list[PayReading] = []
    i = 0
    while i < len(tokens):
        a = tokens[i]
        b = tokens[i + 1] if i + 1 < len(tokens) else None
        pair = _as_range(text, a, b) if b else None
        if pair and b:
            if a.currency or b.currency:
                readings.append(_range(text, a, b, *pair))
            i += 2
            continue
        if a.currency:
            readings.append(_single(text, a))
        i += 1
    return readings
