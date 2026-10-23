"""Reading a job board for a careers page audit: the public job board APIs of Greenhouse, Lever, Ashby and
SmartRecruiters first, then the careers page itself (its embedded board, or the schema.org JobPosting data on its
job pages). Job sites such as LinkedIn, Indeed and Glassdoor are read like any other page, when their robots.txt
lets us; in October 2026 LinkedIn's refused every crawler it hadn't approved, and Indeed and Glassdoor answered
automated readers with a CAPTCHA page, which we don't get past.

Each posting's text is what applicants read on the board: the description plus the pay and AI notes the board
shows beside it. It is returned for the check and never stored.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, cast
from urllib.parse import quote, urljoin, urlsplit

from app.audit.fetch import Fetcher, FetchError
from app.audit.pages import job_postings, places, read_page, to_text, unescaped
from app.audit.places import Where, vague, where

Source = Literal["greenhouse", "lever", "ashby", "smartrecruiters", "page"]
MAX_PAGE_BYTES = 3_000_000
MAX_JOB_PAGES = 25  # job pages read from one careers page
SMARTRECRUITERS_MAX = 1000  # postings listed from one SmartRecruiters company


class NoPostings(FetchError):
    """The page was read, but no job postings were found on it."""


@dataclass
class Found:
    id: str  # the board's id for the posting; a careers page's posting is known by its address
    title: str
    location: str | None  # as the board shows it
    url: str  # the posting's public page
    where: Where
    text: str | None = None  # the posting as applicants read it, when the board's list carries it

    def __post_init__(self) -> None:
        self.title = " ".join(self.title.split())


@dataclass
class Board:
    source: Source
    key: str  # the board's name at the ATS (its token); for a careers page, the page's address
    name: str | None  # the company's name, when the board gives it
    url: str  # the page that was read
    postings: list[Found]


# Which board an address belongs to

_BOARDS: list[tuple[Source, re.Pattern[str]]] = [
    ("greenhouse", re.compile(
        r"(?:job-)?boards(?:-api)?\.greenhouse\.io/(?:embed/job_board(?:/js)?\?(?:[^\s\"'<>]*&)?for=|v1/boards/)?"
        r"([A-Za-z0-9_-]+)"
    )),
    ("lever", re.compile(r"(?:jobs|api)\.lever\.co/(?:v0/postings/)?([A-Za-z0-9_.-]+)")),
    ("ashby", re.compile(r"(?:jobs\.ashbyhq\.com|api\.ashbyhq\.com/posting-api/job-board)/([A-Za-z0-9_.%-]+)")),
    ("smartrecruiters", re.compile(
        r"(?:(?:jobs|careers)\.smartrecruiters\.com|api\.smartrecruiters\.com/v1/companies)/([A-Za-z0-9_.-]+)"
    )),
]  # fmt: skip
_NOT_A_BOARD = {"embed", "v1", "v0", "api", "jobs", "posting-api", "job-board", "companies", "js", "static", "assets"}


def board_in(address: str) -> tuple[Source, str] | None:
    """The ATS board an address points to, from the board's own address or an embed's."""
    for source, pattern in _BOARDS:
        for match in pattern.finditer(address):
            key = match.group(1).strip(".")
            if key and key.lower() not in _NOT_A_BOARD:
                return source, key
    return None


def read_board(url: str, fetcher: Fetcher, today: date) -> Board:
    """Every open posting on the board or careers page at `url`."""
    if found := board_in(url):
        return _READERS[found[0]](found[1], fetcher)
    return _careers_page(url, fetcher, today)


def posting_text(source: Source, key: str, posting: str, url: str, fetcher: Fetcher, today: date) -> str:
    """One posting's text, read again from the board (the check after an hour, or one the board's list omits)."""
    if source == "greenhouse":
        return _greenhouse_text(key, posting, fetcher)
    if source == "lever":
        return _lever_text(_json_dict(fetcher.json(f"https://api.lever.co/v0/postings/{_q(key)}/{_q(posting)}")))
    if source == "smartrecruiters":
        return _smartrecruiters_text(key, posting, fetcher)
    postings = _ashby(key, fetcher).postings if source == "ashby" else _page_postings(url, fetcher, today)
    if (found := next((p for p in postings if p.id == posting), None)) and found.text:
        return found.text
    raise FetchError("This posting isn't on the job board anymore.")


# Helpers


def _q(value: str) -> str:
    return quote(value, safe="")


def _json_dict(data: object) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise FetchError("The job board sent something we couldn't read. Try again later.")
    return cast(dict[str, Any], data)


def _json_list(data: object, key: str | None = None) -> list[dict[str, Any]]:
    items = _json_dict(data).get(key) if key else data
    if not isinstance(items, list):
        raise FetchError("The job board sent something we couldn't read. Try again later.")
    return [item for item in items if isinstance(item, dict)]


def _compose(title: str, location: str | None, *parts: str | None) -> str:
    """The posting as the board page lays it out: title, location, then each part."""
    head = "\n".join(line for line in (title.strip(), (location or "").strip()) if line)
    return "\n\n".join([head, *(part.strip() for part in parts if part and part.strip())])


def _money(value: Any) -> str:
    amount = Decimal(str(value))
    return f"${amount:,.2f}" if amount != amount.to_integral() else f"${amount:,.0f}"


# Greenhouse: https://developers.greenhouse.io/job-board.html


def _greenhouse(token: str, fetcher: Fetcher) -> Board:
    jobs = _json_list(fetcher.json(f"https://boards-api.greenhouse.io/v1/boards/{_q(token)}/jobs?content=true"), "jobs")
    postings = []
    for job in (job for job in jobs if job.get("id")):
        name = (job.get("location") or {}).get("name") or ""
        offices = [office.get("location") or office.get("name") or "" for office in job.get("offices") or []]
        title = str(job.get("title") or "").strip()
        postings.append(Found(
            id=str(job["id"]), title=title, location=name or None, url=str(job.get("absolute_url") or ""),
            where=where(offices if vague(name) else [name], title=title),
        ))  # fmt: skip
    company = next((str(job["company_name"]) for job in jobs if job.get("company_name")), None)
    return Board("greenhouse", token, company, f"https://boards.greenhouse.io/{token}", postings)


def _greenhouse_text(token: str, posting: str, fetcher: Fetcher) -> str:
    job = _json_dict(fetcher.json(
        f"https://boards-api.greenhouse.io/v1/boards/{_q(token)}/jobs/{_q(posting)}?pay_transparency=true"
    ))  # fmt: skip
    pay = []
    for band in job.get("pay_input_ranges") or []:
        low, high = band.get("min_cents"), band.get("max_cents")
        if low is None or high is None:
            continue
        figures = f"{_money(Decimal(low) / 100)} - {_money(Decimal(high) / 100)} {band.get('currency_type') or ''}"
        pay.append("\n".join(filter(None, [band.get("title"), figures.strip(), to_text(band.get("blurb"))])))
    ai = job.get("ai_disclaimer") if job.get("include_ai_disclaimer") else None
    return _compose(
        str(job.get("title") or ""), (job.get("location") or {}).get("name"),
        to_text(unescaped(str(job.get("content") or ""))), *pay, to_text(ai),
    )  # fmt: skip


# Lever: https://github.com/lever/postings-api

_LEVER_PERIOD = {
    "per-hour-wage": "per hour", "per-day-wage": "per day", "per-week-salary": "per week",
    "per-month-salary": "per month", "per-year-salary": "per year",
}  # fmt: skip


def _lever(site: str, fetcher: Fetcher) -> Board:
    jobs = _json_list(fetcher.json(f"https://api.lever.co/v0/postings/{_q(site)}?mode=json"))
    postings = []
    for job in (job for job in jobs if job.get("id")):
        categories = job.get("categories") or {}
        locations = categories.get("allLocations") or [categories.get("location") or ""]
        title = str(job.get("text") or "").strip()
        remote = job.get("workplaceType") == "remote"
        postings.append(Found(
            id=str(job["id"]), title=title, location=", ".join(locations) or None,
            url=str(job.get("hostedUrl") or ""), text=_lever_text(job),
            where=where(locations, remote=remote, country=job.get("country"), title=title),
        ))  # fmt: skip
    return Board("lever", site, None, f"https://jobs.lever.co/{site}", postings)


def _lever_text(job: dict[str, Any]) -> str:
    categories = job.get("categories") or {}
    lists = [f"{item.get('text') or ''}\n{to_text(item.get('content'))}" for item in job.get("lists") or []]
    pay = None
    if (salary := job.get("salaryRange")) and salary.get("min") is not None and salary.get("max") is not None:
        currency = salary.get("currency") or ""
        period = _LEVER_PERIOD.get(salary.get("interval") or "", "")
        pay = f"{_money(salary['min'])} - {_money(salary['max'])} {currency} {period}".replace("  ", " ")
    return _compose(
        str(job.get("text") or ""),
        " / ".join(filter(None, [categories.get("location"), categories.get("department"), categories.get("commitment")])),
        job.get("descriptionPlain") or to_text(job.get("description")), *lists,
        job.get("additionalPlain") or to_text(job.get("additional")), pay, job.get("salaryDescriptionPlain"),
    )  # fmt: skip


# Ashby: https://developers.ashbyhq.com/docs/public-job-posting-api


def _ashby(name: str, fetcher: Fetcher) -> Board:
    data = fetcher.json(f"https://api.ashbyhq.com/posting-api/job-board/{_q(name)}?includeCompensation=true")
    postings = []
    for job in _json_list(data, "jobs"):
        if not job.get("id") or job.get("isListed") is False:
            continue
        locations, country = [str(job.get("location") or "")], None
        for place in [job, *(job.get("secondaryLocations") or [])]:
            address = (place.get("address") or {}).get("postalAddress") or {}
            parts = [address.get(key) for key in ("addressLocality", "addressRegion", "addressCountry")]
            locations += [str(place.get("location") or ""), ", ".join(str(part) for part in parts if part)]
            country = country or address.get("addressCountry")
        shown = [job.get("location"), *(place.get("location") for place in job.get("secondaryLocations") or [])]
        title = str(job.get("title") or "").strip()
        postings.append(Found(
            id=str(job["id"]), title=title,
            location=" • ".join(dict.fromkeys(str(name) for name in shown if name)) or None,
            url=str(job.get("jobUrl") or ""), text=_ashby_text(job),
            where=where(locations, remote=bool(job.get("isRemote")), country=country, title=title),
        ))  # fmt: skip
    return Board("ashby", name, None, f"https://jobs.ashbyhq.com/{name}", postings)


def _ashby_text(job: dict[str, Any]) -> str:
    names = [job.get("location"), *(place.get("location") for place in job.get("secondaryLocations") or [])]
    pay = None
    compensation = job.get("compensation") or {}
    if job.get("shouldDisplayCompensationOnJobPostings") and compensation:
        tiers = [
            ": ".join(filter(None, [tier.get("title"), tier.get("tierSummary")]))
            for tier in compensation.get("compensationTiers") or []
        ]  # fmt: skip
        pay = "Compensation\n" + "\n".join(tiers or [compensation.get("compensationTierSummary") or ""])
    return _compose(
        str(job.get("title") or ""), " • ".join(filter(None, names)),
        job.get("descriptionPlain") or to_text(job.get("descriptionHtml")), pay,
    )  # fmt: skip


# SmartRecruiters: https://developers.smartrecruiters.com/docs/posting-api


def _smartrecruiters(company: str, fetcher: Fetcher) -> Board:
    postings, name, offset = [], None, 0
    while offset < SMARTRECRUITERS_MAX:
        page = _json_dict(fetcher.json(
            f"https://api.smartrecruiters.com/v1/companies/{_q(company)}/postings?limit=100&offset={offset}"
        ))  # fmt: skip
        jobs = _json_list(page, "content")
        for job in (job for job in jobs if job.get("id")):
            place = job.get("location") or {}
            line = place.get("fullLocation") or ", ".join(
                str(place[key]) for key in ("city", "region", "country") if place.get(key)
            )  # fmt: skip
            name = name or (job.get("company") or {}).get("name")
            title = str(job.get("name") or "").strip()
            postings.append(Found(
                id=str(job["id"]), title=title, location=line or None,
                url=f"https://jobs.smartrecruiters.com/{company}/{job['id']}",
                where=where([line], remote=bool(place.get("remote")), country=place.get("country"), title=title),
            ))  # fmt: skip
        offset += len(jobs)
        if not jobs or offset >= int(page.get("totalFound") or 0):
            break
    return Board("smartrecruiters", company, name, f"https://jobs.smartrecruiters.com/{company}", postings)


def _smartrecruiters_text(company: str, posting: str, fetcher: Fetcher) -> str:
    job = _json_dict(fetcher.json(f"https://api.smartrecruiters.com/v1/companies/{_q(company)}/postings/{_q(posting)}"))
    place = job.get("location") or {}
    sections = ((job.get("jobAd") or {}).get("sections")) or {}
    parts = [
        "\n".join(filter(None, [section.get("title"), to_text(section.get("text"))]))
        for key in ("companyDescription", "jobDescription", "qualifications", "additionalInformation")
        if isinstance(section := sections.get(key), dict)
    ]  # fmt: skip
    location = place.get("fullLocation") or ", ".join(str(place[k]) for k in ("city", "region") if place.get(k))
    return _compose(str(job.get("name") or ""), location, *parts)


_READERS: dict[Source, Callable[[str, Fetcher], Board]] = {
    "greenhouse": _greenhouse, "lever": _lever, "ashby": _ashby, "smartrecruiters": _smartrecruiters,
}  # fmt: skip


# A careers page: its embedded board, or the JobPosting data on the page and on its job pages

_JOB_LINK = re.compile(r"/(?:jobs?|careers?|positions?|openings?|opportunit(?:y|ies)|vacanc(?:y|ies)|postings?|roles?)"
                       r"(?:/|$|\?|-|_)", re.IGNORECASE)  # fmt: skip
_PERIOD = {"HOUR": "per hour", "DAY": "per day", "WEEK": "per week", "MONTH": "per month", "YEAR": "per year"}


def _careers_page(url: str, fetcher: Fetcher, today: date) -> Board:
    markup, final = fetcher.text(url, MAX_PAGE_BYTES)
    page = read_page(markup)
    for address in [str(final), *page.sources, *(href for href, _ in page.links)]:
        if found := board_in(address):
            return _READERS[found[0]](found[1], fetcher)
    name = page.site_name or None
    postings = _postings_in(page.json_ld, str(final), today)
    if not postings:
        seen, links = {str(final)}, []
        for href, _ in page.links:
            link = urljoin(str(final), href).split("#")[0]
            if link not in seen and _same_site(link, str(final)) and _JOB_LINK.search(urlsplit(link).path):
                seen.add(link)
                links.append(link)
        for link in links[:MAX_JOB_PAGES]:
            try:
                postings += _page_postings(link, fetcher, today)
            except FetchError:  # a page we may not or can't read is left out
                continue
    if not postings:
        raise NoPostings(
            "We couldn't find job postings on that page. Enter your job board's address (Greenhouse, Lever, Ashby "
            "or SmartRecruiters), or the careers page that lists your openings."
        )  # fmt: skip
    unique = {posting.id: posting for posting in postings}
    return Board("page", str(final), name, str(final), list(unique.values()))


def _same_site(link: str, page: str) -> bool:
    host, base = urlsplit(link).hostname or "", (urlsplit(page).hostname or "").removeprefix("www.")
    return urlsplit(link).scheme in ("http", "https") and (host.removeprefix("www.") == base or host.endswith("." + base))


def _page_postings(url: str, fetcher: Fetcher, today: date) -> list[Found]:
    """The postings in a page's JSON-LD; none when the page carries no JobPosting data."""
    markup, final = fetcher.text(url.split("#")[0], MAX_PAGE_BYTES)
    return _postings_in(read_page(markup).json_ld, str(final), today)


def _postings_in(json_ld: list[Any], page: str, today: date) -> list[Found]:
    return [found for posting in job_postings(json_ld) if (found := _from_json_ld(posting, page, today))]


def _from_json_ld(posting: dict[str, Any], page: str, today: date) -> Found | None:
    """A schema.org JobPosting, unless it closed before today."""
    closes = str(posting.get("validThrough") or "")[:10]
    try:
        if closes and datetime.fromisoformat(closes).date() < today:
            return None
    except ValueError:
        pass
    title = str(posting.get("title") or "").strip()
    if not title:
        return None
    lines, remote, country = places(posting)
    url = str(posting.get("url") or "") or f"{page}#{re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')}"
    pay = None
    if isinstance(salary := posting.get("baseSalary"), dict) and isinstance(value := salary.get("value"), dict):
        low, high = value.get("minValue", value.get("value")), value.get("maxValue", value.get("value"))
        if low is not None and high is not None:
            period = _PERIOD.get(str(value.get("unitText") or "").upper(), "")
            figures = _money(low) if str(low) == str(high) else f"{_money(low)} - {_money(high)}"
            pay = f"Pay: {figures} {salary.get('currency') or ''} {period}".replace("  ", " ").strip()
    description = str(posting.get("description") or "")
    if "&lt;" in description:  # HTML escaped once more
        description = unescaped(description)
    text = _compose(title, "; ".join(lines), to_text(description), pay)
    return Found(id=url, title=title, location="; ".join(lines) or None, url=url, text=text,
                 where=where(lines, remote=remote, country=country, title=title))  # fmt: skip
