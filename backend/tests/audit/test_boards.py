"""Reading job boards from recorded responses: which postings are for work in Ontario, and each posting's text as
applicants read it on the board, pay and AI notes included."""

import json
from datetime import date
from decimal import Decimal

import pytest

from app.audit.boards import Board, NoPostings, board_in, posting_text, read_board
from app.audit.fetch import FetchError, RobotsRefused
from app.compliance.money import parse_pay
from tests.audit.web import Web, boards, smartrecruiters_allowed

TODAY = date(2026, 10, 22)


def by_title(board):  # type: ignore[no-untyped-def]
    return {posting.title: posting for posting in board.postings}


@pytest.mark.parametrize(("address", "expected"), [
    ("https://boards.greenhouse.io/faire", ("greenhouse", "faire")),
    ("https://job-boards.greenhouse.io/faire/jobs/8821336002", ("greenhouse", "faire")),
    ("https://boards.greenhouse.io/embed/job_board/js?for=faire", ("greenhouse", "faire")),
    ("https://boards.greenhouse.io/embed/job_board?b=1&for=faire", ("greenhouse", "faire")),
    ("https://jobs.lever.co/achievers/cfd24914-023d", ("lever", "achievers")),
    ("https://jobs.ashbyhq.com/cohere", ("ashby", "cohere")),
    ("https://jobs.smartrecruiters.com/NorthwindLogistics/744000012345671", ("smartrecruiters", "NorthwindLogistics")),
    ("https://careers.smartrecruiters.com/NorthwindLogistics", ("smartrecruiters", "NorthwindLogistics")),
    ("https://maplegrocers.ca/careers", None),
])  # fmt: skip
def test_board_in(address: str, expected: tuple[str, str] | None) -> None:
    assert board_in(address) == expected


def test_greenhouse() -> None:
    web = boards()
    board = read_board("https://boards.greenhouse.io/faire", web.fetcher(), TODAY)
    assert (board.source, board.key, board.name) == ("greenhouse", "faire", "Faire")
    found = {p.title + " | " + (p.location or ""): p.where for p in board.postings}
    assert found == {
        "Customer Experience Associate (3 Month Fixed-Term Contract) | Kitchener-Waterloo, ON": "ontario",
        "Growth Platform, Marketing Engineer | Toronto, ON": "ontario",
        # the same job in New York and San Francisco: its offices list Toronto, but its location doesn't
        "Growth Platform, Marketing Engineer | New York City, NY; San Francisco, CA": "elsewhere",
        "Director, Global Equity | Remote - US": "elsewhere",
    }
    toronto = next(p for p in board.postings if p.location == "Toronto, ON")
    assert toronto.url == "https://boards.greenhouse.io/faire/jobs/8821336002?gh_jid=8821336002"
    assert toronto.text is None  # read when it's checked, with its pay range
    text = posting_text("greenhouse", "faire", toronto.id, toronto.url, web.fetcher(), TODAY)
    assert text.startswith("Growth Platform, Marketing Engineer\nToronto, ON\n\nAbout the role\n")
    assert "• Answer customer questions\n• Keep records up to date" in text
    assert "Toronto pay range\n$90,000 - $110,000 CAD\nPay depends on experience." in text
    assert text.endswith("We use AI to screen applications for this job.")  # the board's AI note, shown on the page


def test_lever() -> None:
    web = boards()
    board = read_board("https://jobs.lever.co/achievers", web.fetcher(), TODAY)
    postings = by_title(board)
    assert {title: p.where for title, p in postings.items()} == {
        "Accounts Receivable and Collection Specialist": "ontario",
        "Finance Manager, Marketplace ⭐": "canada",  # remote, anywhere in Canada
        "Mid-Market Account Executive": "elsewhere",
        "Senior Deal Desk Analyst ⭐": "elsewhere",
        "Pharmacist - FT or PT - Trail, BC": "elsewhere",  # the location says only Canada; the title names BC
    }
    text = postings["Accounts Receivable and Collection Specialist"].text
    assert text is not None and text.startswith(
        "Accounts Receivable and Collection Specialist\nToronto / Corporate Operations / Full-time permanent\n\n"
    )
    assert "What you bring\n• 2 years in accounts receivable\n• Clear writing" in text
    assert "We welcome applications from people with disabilities." in text
    assert text.endswith("$60,000 - $70,000 CAD per year")
    assert web.sleeps == []  # one request: Lever's Crawl-delay never had to wait


def test_ashby() -> None:
    board = read_board("https://jobs.ashbyhq.com/cohere", boards().fetcher(), TODAY)  # robots.txt 401: no rules
    postings = by_title(board)
    assert {title: (p.location, p.where) for title, p in postings.items()} == {
        "Senior Full-Stack Engineer, Internal Applications": ("Toronto • Canada", "ontario"),
        "Member of Technical Staff, Modeling": ("London • San Francisco • New York • Paris • Toronto • Montreal", "ontario"),
        "Revenue Enablement Manager - EMEA": ("Europe • London", "elsewhere"),
        "Solutions Architect - Public Sector": ("Washington, DC", "elsewhere"),
    }  # fmt: skip
    text = postings["Senior Full-Stack Engineer, Internal Applications"].text
    assert text is not None and text.endswith("Compensation\nCanada: Base Salary CA$215K – CA$295K • Offers Equity")


def test_smartrecruiters_asks_bots_to_stay_out() -> None:
    with pytest.raises(RobotsRefused, match="api.smartrecruiters.com"):
        read_board("https://jobs.smartrecruiters.com/NorthwindLogistics", boards().fetcher(), TODAY)


def test_smartrecruiters_when_allowed() -> None:
    web = smartrecruiters_allowed(boards())
    board = read_board("https://jobs.smartrecruiters.com/NorthwindLogistics", web.fetcher(), TODAY)
    assert board.name == "Northwind Logistics"
    assert [(p.title, p.where) for p in board.postings] == [
        ("Warehouse Associate", "ontario"), ("Dispatcher", "elsewhere"), ("Payroll Specialist", "canada"),
    ]  # two pages of results
    text = posting_text("smartrecruiters", "NorthwindLogistics", "744000012345671", "", web.fetcher(), TODAY)
    assert text == (
        "Warehouse Associate\nMississauga, ON, Canada\n\nCompany Description\nNorthwind moves freight across Ontario."
        "\n\nJob Description\n• Pick and pack orders\n• Load trucks safely\n\nQualifications\nAble to lift 50 lb."
        "\n\nAdditional Information\nPay: $19.00 - $21.00 an hour."
    )  # fmt: skip


def test_a_careers_page_with_job_pages() -> None:
    web = boards()
    board = read_board("https://maplegrocers.ca/careers", web.fetcher(), TODAY)
    assert (board.source, board.name) == ("page", "Maple Grocers")
    assert [(p.title, p.location, p.where) for p in board.postings] == [
        ("Store Manager", "Toronto, ON, CA", "ontario"),
        ("Cashier", "Ottawa, Ontario, Canada", "ontario"),
        ("Buyer", "Vancouver, BC, CA", "elsewhere"),
    ]  # the closed seasonal posting, the team page and other sites' links are left out
    assert "elsewhere.example/careers/not-ours" not in web.asked()
    assert not any("linkedin" in address for address in web.asked())
    store, cashier = board.postings[0], board.postings[1]
    assert store.text == (
        "Store Manager\nToronto, ON, CA\n\nLead a team of 30 at our Queen Street store.\n\n• 3 years managing a grocery "
        "store\n\nPay: $65,000 - $75,000 CAD per year"
    )  # fmt: skip
    assert cashier.id == "https://maplegrocers.ca/careers/cashier-ottawa#cashier"  # no url in its data
    assert cashier.text is not None and cashier.text.endswith("Pay: $17.60 CAD per hour")
    again = posting_text("page", board.key, cashier.id, cashier.url, web.fetcher(), TODAY)
    assert again == cashier.text


def _job(title: str, value: dict[str, object]) -> dict[str, object]:
    address = {"addressLocality": "Toronto", "addressRegion": "ON", "addressCountry": "CA"}
    return {
        "@type": "JobPosting", "title": title, "description": "<p>Answer the phones.</p>",
        "url": f"https://ghrc.example/jobs/{title.lower()}", "jobLocation": {"address": address},
        "baseSalary": {"currency": "CAD", "value": {"@type": "QuantitativeValue", "unitText": "HOUR", **value}},
    }  # fmt: skip


def _read(*postings: dict[str, object]) -> Board:
    markup = f'<script type="application/ld+json">{json.dumps(list(postings))}</script>'
    return read_board("https://ghrc.example/jobs", Web().page("ghrc.example/jobs", markup).fetcher(), TODAY)


@pytest.mark.parametrize(("value", "pay", "low", "high"), [
    ({"value": "$80,000.00-$95,000.00", "unitText": "YEAR"}, "$80,000.00-$95,000.00 CAD per year", "80000", "95000"),  # ghrc.ca
    ({"value": "19.50-20.00"}, "19.50-20.00 CAD per hour", "19.50", "20"),  # ghrc.ca
    ({"minValue": "$20/hr", "maxValue": "$25/hr"}, "$20/hr - $25/hr CAD per hour", "20", "25"),
    ({"minValue": "60,000", "maxValue": 70000, "unitText": "YEAR"}, "60,000 - $70,000 CAD per year", "60000", "70000"),
])  # fmt: skip
def test_pay_written_as_text_stays_as_the_page_wrote_it(
    value: dict[str, object], pay: str, low: str, high: str
) -> None:
    posting = _read(_job("Receptionist", value)).postings[0]
    assert posting.text == f"Receptionist\nToronto, ON, CA\n\nAnswer the phones.\n\nPay: {pay}"
    reading = parse_pay(posting.text)[0]
    assert (reading.min, reading.max) == (Decimal(low), Decimal(high))


@pytest.mark.parametrize(("value", "pay"), [
    ("$20 - $25 an hour", "$20 - $25 an hour CAD"),
    (25, "$25 CAD"),
])  # fmt: skip
def test_pay_beside_the_currency_with_no_quantity_around_it(value: object, pay: str) -> None:
    job = {**_job("Receptionist", {}), "baseSalary": {"currency": "CAD", "value": value}}
    assert _read(job).postings[0].text == f"Receptionist\nToronto, ON, CA\n\nAnswer the phones.\n\nPay: {pay}"


@pytest.mark.parametrize("value", [
    {"value": "Competitive"},
    {"minValue": 20, "maxValue": "Depends on experience"},
    {"minValue": "To be discussed", "maxValue": 25},
    {"value": "NaN"},
    {"value": "Infinity"},
    {"value": ""},
    {"value": {"nested": 25}},
])  # fmt: skip
def test_pay_without_a_figure_is_skipped_and_the_board_is_still_read(value: dict[str, object]) -> None:
    board = _read(_job("Receptionist", value), _job("Dispatcher", {"minValue": 20, "maxValue": 25.5}))
    receptionist, dispatcher = board.postings
    assert (receptionist.title, receptionist.where) == ("Receptionist", "ontario")
    assert receptionist.text == "Receptionist\nToronto, ON, CA\n\nAnswer the phones."
    assert dispatcher.text == "Dispatcher\nToronto, ON, CA\n\nAnswer the phones.\n\nPay: $20 - $25.50 CAD per hour"


def test_a_careers_page_with_an_embedded_board() -> None:
    board = read_board("https://www.faire.com/careers", boards().fetcher(), TODAY)
    assert (board.source, board.key, len(board.postings)) == ("greenhouse", "faire", 4)


def test_a_page_without_postings() -> None:
    web = boards().page("example.ca/careers", "<h1>No openings right now</h1>")
    with pytest.raises(NoPostings):
        read_board("https://example.ca/careers", web.fetcher(), TODAY)


def test_job_sites_are_read_like_any_page_their_robots_txt_allows() -> None:
    web = boards()
    # LinkedIn's robots.txt ends with these lines: crawlers it hasn't approved are refused
    web.page("www.linkedin.com/robots.txt", "User-agent: Googlebot\nAllow: /jobs/\n\nUser-agent: *\nDisallow: /\n")
    with pytest.raises(RobotsRefused, match="www.linkedin.com"):
        read_board("https://www.linkedin.com/jobs/view/123", web.fetcher(), TODAY)
    # Indeed and Glassdoor allow some job pages, but answer automated readers with a CAPTCHA page
    web.page("ca.indeed.com/robots.txt", "User-agent: *\nAllow: /\nDisallow: /viewjob\n")
    web.page("ca.indeed.com/cmp/Northwind/jobs", "<p>Verify you are human</p>", status=403)
    with pytest.raises(FetchError, match="ca.indeed.com blocks automated readers"):
        read_board("https://ca.indeed.com/cmp/Northwind/jobs", web.fetcher(), TODAY)
    with pytest.raises(RobotsRefused):
        read_board("https://ca.indeed.com/viewjob?jk=abc", web.fetcher(), TODAY)
    # a job site page we may read, with the posting's data on it, is read like a careers page
    web.page("www.glassdoor.ca/robots.txt", "User-agent: *\nDisallow: /jobview/\n")
    web.file("www.glassdoor.ca/job-listing/store-manager-JV_IC1.htm", "job_store_manager.html")
    board = read_board("https://www.glassdoor.ca/job-listing/store-manager-JV_IC1.htm", web.fetcher(), TODAY)
    assert [(p.title, p.where) for p in board.postings] == [("Store Manager", "ontario")]
