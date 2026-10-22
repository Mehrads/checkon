"""Pay range suggestions for a paying customer's posting (PRD FR9, Technical Design §9).

A suggestion is a range the employer can confirm or edit; it never goes into the posting by itself. Its sources,
in order:

1. a range the customer confirmed earlier for the same job title, in their company profile or client workspace;
2. Job Bank wages for the occupation (NOC 2021) in the work location's economic region;
3. pay quoted from current postings for the same title and place, found by a web search.

The model only names the occupation and quotes postings. Every figure is read from Job Bank's file, or by the
money parser from the quoted text; the arithmetic (units, the suggested range, the yearly cap) is code.
"""

import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from statistics import median
from typing import Any, Literal, Protocol
from urllib.parse import urlsplit

from pydantic import BaseModel

from app.compliance.checks import annualise
from app.compliance.employer import MAX_SEARCHES, place_key
from app.compliance.extraction import PROMPTS_DIR
from app.compliance.llm import Cited, CitingLLM, LLMError, ModelSettings, StructuredLLM
from app.compliance.models import PayUnit
from app.compliance.money import format_pay, parse_pay
from app.pay.jobbank import JobBank, Wage, plain

# Naming the occupation: Haiku 5.5 with thinking at low effort. With thinking off, a live sample matched
# "Payroll Specialist" to bookkeepers rather than payroll administrators.
OCCUPATION_SETTINGS = ModelSettings(max_tokens=3000, effort="low", thinking={"type": "adaptive"})
# Job sites whose terms forbid scraping, or that republish them (PRD §7, §10): never searched, never shown.
BLOCKED_SITES = (
    "glassdoor.com", "glassdoor.ca", "indeed.com", "indeed.ca", "linkedin.com", "simplyhired.com", "simplyhired.ca",
)  # fmt: skip
SEARCH_DAYS = 7  # a postings search is reused for a week
MAX_AGE_DAYS = 365  # older postings aren't current
FAR_BELOW, FAR_ABOVE = Decimal("0.8"), Decimal("1.2")  # a band's midpoint against the market median
SPREAD = Decimal("0.1")  # without Job Bank's quartiles, a suggestion spans the median ± 10%
STEP = {PayUnit.HOUR: Decimal("0.25"), PayUnit.WEEK: Decimal(10), PayUnit.MONTH: Decimal(100), PayUnit.YEAR: Decimal(1000)}
PRECISION = {PayUnit.HOUR: Decimal("0.01"), PayUnit.WEEK: Decimal(1), PayUnit.MONTH: Decimal(1), PayUnit.YEAR: Decimal(1)}

_CUT_OFF = re.compile(r"\s*[-–—]\s*(?:\.\.\.|…)")  # "$80,000 -...": the snippet ended mid-range
_AGO = re.compile(r"(?:(\d+)|an?)\s+(day|week|month|year)s?\s+ago", re.IGNORECASE)
_DAYS = {"day": 1, "week": 7, "month": 30, "year": 365}
_DATES = ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%d %B %Y")


class OccupationMatch(BaseModel):
    code: str  # NOC 2021 unit group
    confidence: Literal["high", "medium", "low"]
    alternative: str | None  # the next most likely unit group


class Occupation(BaseModel):
    code: str
    title: str


class PayRange(BaseModel):
    min: Decimal
    max: Decimal
    unit: PayUnit


class MarketRange(BaseModel):
    low: Decimal | None
    median: Decimal
    high: Decimal | None
    unit: PayUnit
    basis: Literal["job_bank", "postings"]


class PostingPay(BaseModel):
    """Pay read by the money parser from a posting the search quoted."""

    url: str
    site: str
    title: str | None
    quote: str  # the text the figures were read from
    min: Decimal
    max: Decimal
    unit: PayUnit
    posted: str | None  # the page's age as the search reported it


class PostingSearch(BaseModel):
    searched_on: date
    postings: list[PostingPay]


class PostingCache(Protocol):
    """Postings searches by job title and place, kept for a week (Postgres in the app: app/api/pay_cache.py)."""

    def get(self, key: tuple[str, str]) -> PostingSearch | None: ...
    def put(self, key: tuple[str, str], value: PostingSearch) -> None: ...


class ConfirmedBand(BaseModel):
    """A range the customer confirmed earlier for this job title."""

    title: str
    range: PayRange
    confirmed_on: date


class Source(BaseModel):
    kind: Literal["band", "job_bank", "posting"]
    name: str
    figures: str  # as the source gives them, in its own unit
    url: str | None = None
    date: str | None = None
    quote: str | None = None
    licence: str | None = None
    licence_url: str | None = None


class Suggestion(BaseModel):
    """`pick_occupation`: the posting fits two occupations about equally, so the user picks one of
    `alternatives` and asks again. Otherwise `suggested` is within the yearly cap, in `market`'s unit."""

    status: Literal["suggested", "pick_occupation"]
    occupation: Occupation | None = None
    alternatives: list[Occupation] = []
    region: str | None = None
    suggested: PayRange | None = None
    market: MarketRange | None = None
    band: PayRange | None = None
    flag: Literal["below_market", "above_market"] | None = None
    hours_per_week: Decimal  # hourly and yearly figures are compared at these hours
    max_annual_width: Decimal  # the legal limit on a range's width, a year
    sources: list[Source] = []
    notes: list[str] = []


class PayLLM(StructuredLLM, CitingLLM, Protocol):
    pass


def role_key(title: str) -> str:
    """A job title as the key of a confirmed band: "Payroll Specialist (Bilingual)" is "payroll specialist bilingual"."""
    return plain(title)[:255]


def _day(value: date) -> str:
    return value.strftime("%B %-d, %Y")


# The occupation


def map_occupation(
    title: str, posting: str, job_bank: JobBank, llm: StructuredLLM, settings: ModelSettings = OCCUPATION_SETTINGS
) -> OccupationMatch:
    listed = "\n".join(f"{code} {name}" for code, name in job_bank.occupations.items())
    system = (PROMPTS_DIR / "noc_map.md").read_text(encoding="utf-8").replace("{{OCCUPATIONS}}", listed)
    user = f"<job_title>{title}</job_title>\n<posting>\n{posting}\n</posting>"
    match = llm.parse(system=system, user=user, schema=OccupationMatch, settings=settings)
    if match.code not in job_bank.occupations:
        raise LLMError(f"the occupation code {match.code!r} isn't in NOC 2021")
    if match.alternative not in job_bank.occupations or match.alternative == match.code:
        match = match.model_copy(update={"alternative": None})
    return match


# Current postings


def search_tool() -> dict[str, Any]:
    return {
        "type": "web_search_20250305", "name": "web_search", "max_uses": MAX_SEARCHES,
        "user_location": {"type": "approximate", "country": "CA", "region": "Ontario"},
        "blocked_domains": list(BLOCKED_SITES),
    }  # fmt: skip


def blocked(host: str) -> bool:
    return any(host == site or host.endswith("." + site) for site in BLOCKED_SITES)


def age_in_days(page_age: str | None, today: date) -> int | None:
    """"105 days ago", "a year ago" or a date, as the search reports a page's age; None when it can't tell."""
    if not page_age:
        return None
    if found := _AGO.search(page_age):
        return int(found.group(1) or 1) * _DAYS[found.group(2).lower()]
    for layout in _DATES:
        try:
            return (today - datetime.strptime(page_age.strip(), layout).date()).days
        except ValueError:
            continue
    return None


def postings_from(cited: Cited, today: date) -> list[PostingPay]:
    """Pay in the quoted sentences, read by the money parser. Postings over a year old, ranges cut off in the
    quote, amounts in other currencies or with no period, and blocked sites are left out."""
    ages = {result.url: result.page_age for result in cited.results}
    found: dict[tuple[str, Decimal, Decimal, PayUnit], PostingPay] = {}
    for quote in cited.quotes:
        host = urlsplit(quote.url).netloc.lower().removeprefix("www.")
        age = ages.get(quote.url)
        if not host or blocked(host) or (age_in_days(age, today) or 0) > MAX_AGE_DAYS:
            continue
        for reading in parse_pay(quote.text):
            if reading.min is None or reading.max is None or reading.unit is None or reading.currency != "CAD":
                continue
            if _CUT_OFF.match(quote.text, reading.span[1]):
                continue
            found.setdefault((quote.url, reading.min, reading.max, reading.unit), PostingPay(
                url=quote.url, site=host, title=quote.title, quote=quote.text.strip()[:300], min=reading.min,
                max=reading.max, unit=reading.unit, posted=age,
            ))  # fmt: skip
    return list(found.values())


def search_postings(
    title: str, location: str | None, llm: CitingLLM, settings: ModelSettings, today: date,
    cache: PostingCache | None = None,
) -> PostingSearch | None:  # fmt: skip
    """None when the search fails; the suggestion then goes without current postings."""
    key = (role_key(title), place_key(location)[:255])
    if cache is not None and (cached := cache.get(key)) is not None:
        return cached
    user = f"<job_title>{title}</job_title>\n<location>{location or 'Ontario'}</location>"
    system = (PROMPTS_DIR / "pay_postings.md").read_text(encoding="utf-8")
    try:
        cited = llm.cite(system=system, user=user, settings=settings, tools=[search_tool()])
    except LLMError:
        return None
    found = PostingSearch(searched_on=today, postings=postings_from(cited, today))
    if cache is not None:
        cache.put(key, found)
    return found


# The suggestion


@dataclass(frozen=True)
class Units:
    """Converts pay between periods at the job's hours, as the range rule does."""

    hours: Decimal
    params: dict[str, Any]

    def annual(self, amount: Decimal, unit: PayUnit) -> Decimal:
        return annualise(amount, unit, self.hours, self.params)

    def convert(self, amount: Decimal, unit: PayUnit, to: PayUnit) -> Decimal:
        if unit == to:
            return amount
        return (self.annual(amount, unit) / self.annual(Decimal(1), to)).quantize(PRECISION[to])


def _round(value: Decimal, step: Decimal, rounding: str) -> Decimal:
    return (value / step).to_integral_value(rounding) * step


def within_cap(low: Decimal, high: Decimal, unit: PayUnit, units: Units) -> PayRange:
    """The range, narrowed around its middle when it is wider than the yearly cap allows."""
    step = STEP[unit]
    widest = _round(units.params["max_annual_width"] / units.annual(Decimal(1), unit), step, ROUND_FLOOR)
    if high - low > widest:
        low = max(_round((low + high) / 2 - widest / 2, step, ROUND_FLOOR), Decimal(0))
        high = low + widest
    return PayRange(min=low, max=high, unit=unit)


def _around(middle: Decimal, half: Decimal, unit: PayUnit, units: Units) -> PayRange:
    step = STEP[unit]
    low = max(_round(middle - half, step, ROUND_FLOOR), Decimal(0))
    return within_cap(low, _round(middle + half, step, ROUND_CEILING), unit, units)


def _unit(band: ConfirmedBand | None, hint: PayUnit | None, postings: list[PostingPay], wage: Wage | None) -> PayUnit:
    """The band's unit, else the posting's own, else what current postings use, else Job Bank's."""
    if band:
        return band.range.unit
    if hint:
        return hint
    if postings:
        return Counter(posting.unit for posting in postings).most_common(1)[0][0]
    return wage.unit if wage else PayUnit.YEAR


def _market(wage: Wage | None, postings: list[PostingPay], unit: PayUnit, units: Units) -> MarketRange | None:
    if wage is not None and wage.median is not None:
        low, high = (units.convert(v, wage.unit, unit) if v is not None else None for v in (wage.low, wage.high))
        return MarketRange(
            low=low, median=units.convert(wage.median, wage.unit, unit), high=high, unit=unit, basis="job_bank"
        )
    if postings:
        middles = [units.convert((p.min + p.max) / 2, p.unit, unit) for p in postings]
        return MarketRange(
            low=min(units.convert(p.min, p.unit, unit) for p in postings), median=Decimal(median(middles)).quantize(PRECISION[unit]),
            high=max(units.convert(p.max, p.unit, unit) for p in postings), unit=unit, basis="postings",
        )  # fmt: skip
    return None


def _dollars(amount: Decimal) -> str:
    return f"${amount:,.0f}" if amount == amount.to_integral_value() else f"${amount:,.2f}"


def _job_bank_figures(wage: Wage) -> str:
    """"Low $19, median $26.67, high $37.95 an hour": Job Bank's low and high are the 10th and 90th percentiles."""
    figures = [(name, value) for name, value in (("Low", wage.low), ("median", wage.median), ("high", wage.high)) if value]
    per = "a year" if wage.unit == PayUnit.YEAR else "an hour"
    return ", ".join(f"{name} {_dollars(value)}" for name, value in figures) + f" {per}"


def suggest(
    *, title: str, location: str | None, posting: str, hours: Decimal, params: dict[str, Any],
    band: ConfirmedBand | None, unit_hint: PayUnit | None, noc: str | None, job_bank: JobBank, llm: PayLLM,
    today: date, search_settings: ModelSettings, postings_cache: PostingCache | None = None,
) -> Suggestion:  # fmt: skip
    """`noc` is the occupation the user picked; without it the model names one, and when it can't tell between
    two, the user is asked to pick before anything is searched."""
    units = Units(hours, params)
    base = {"hours_per_week": hours, "max_annual_width": params["max_annual_width"]}
    if noc is None:
        match = map_occupation(title, posting, job_bank, llm)
        if match.confidence == "low" and match.alternative:
            choices = [Occupation(code=code, title=job_bank.occupations[code]) for code in (match.code, match.alternative)]
            return Suggestion(status="pick_occupation", alternatives=choices, **base)
        noc, others = match.code, [match.alternative] if match.alternative else []
    elif noc not in job_bank.occupations:
        raise ValueError(f"{noc} isn't an occupation code in NOC 2021.")
    else:
        others = []
    occupation = Occupation(code=noc, title=job_bank.occupations[noc])

    region = job_bank.region_for(location)
    wage = job_bank.wage(noc, region)
    found = search_postings(title, location, llm, search_settings, today, postings_cache)
    postings = found.postings if found else []

    unit = _unit(band, unit_hint, postings, wage)
    market = _market(wage, postings, unit, units)
    notes: list[str] = []
    sources: list[Source] = []
    flag: Literal["below_market", "above_market"] | None = None
    if band:
        suggested: PayRange | None = within_cap(band.range.min, band.range.max, unit, units)
        sources.append(Source(
            kind="band", name=f"Your confirmed range for {band.title}",
            figures=format_pay(band.range.min, band.range.max, band.range.unit), date=f"Confirmed {_day(band.confirmed_on)}",
        ))  # fmt: skip
        if market:
            middle = (band.range.min + band.range.max) / 2
            if middle < market.median * FAR_BELOW:
                flag = "below_market"
            elif middle > market.median * FAR_ABOVE:
                flag = "above_market"
    elif market:
        if wage and wage.median is not None and wage.q1 is not None and wage.q3 is not None:
            half = units.convert((wage.q3 - wage.q1) / 2, wage.unit, unit)
        else:
            half = market.median * SPREAD
        suggested = _around(market.median, half, unit, units)
    else:
        suggested = None
        notes.append("We found no market figures for this job, so there's no range to suggest. Enter the range you expect to pay.")

    region_name = job_bank.regions[region]
    if wage:
        dataset = job_bank.dataset
        place = job_bank.regions[wage.region]
        sources.append(Source(
            kind="job_bank", name=f"Job Bank wages: {occupation.title} (NOC {noc}), {place}",
            figures=_job_bank_figures(wage), url=dataset.url,
            date=f"Published {_day(dataset.published)}, for {wage.period} ({wage.source})",
            licence=dataset.licence, licence_url=dataset.licence_url,
        ))  # fmt: skip
        if wage.region != region:
            notes.append(f"Job Bank has no figures for this occupation in the {region_name} region, so these are Ontario's.")
    else:
        notes.append("Job Bank publishes no wages for this occupation.")
    for p in postings:
        when = f"Posted {p.posted}" if p.posted else f"Found {_day(found.searched_on)}" if found else None
        sources.append(Source(
            kind="posting", name=p.site, figures=format_pay(p.min, p.max, p.unit), url=p.url, date=when,
            quote=p.quote,
        ))  # fmt: skip
    if found is None:
        notes.append("We couldn't search current postings just now.")
    elif not postings:
        notes.append("We found no current postings with pay for this job title nearby.")
    converted = (wage and wage.unit != unit) or any(p.unit != unit for p in postings)
    if converted:
        notes.append(f"Hourly and yearly figures are compared at {hours:g} hours a week.")
    return Suggestion(
        status="suggested", occupation=occupation, alternatives=[Occupation(code=c, title=job_bank.occupations[c]) for c in others],
        region=region_name, suggested=suggested, market=market, band=band.range if band else None, flag=flag,
        sources=sources, notes=notes, **base,
    )  # fmt: skip
