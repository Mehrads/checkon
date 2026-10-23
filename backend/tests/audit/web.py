"""A recorded web for audit tests: job board responses served by host and path, with no network and no DNS.

The Greenhouse, Lever and Ashby files are real responses (2026-10-22) cut to a few postings, with the posting
text replaced by a short made-up one. SmartRecruiters' API asks bots other than LinkedIn's not to read it
(robots.txt), so its files are written from its documented format instead of recorded.
"""

from dataclasses import dataclass, field
from pathlib import Path

import httpx

from app.audit.fetch import Fetcher, HostPacing, RobotsCache

BOARDS = Path(__file__).parent / "boards"
PUBLIC = "93.184.216.34"


def recorded(name: str) -> str:
    return (BOARDS / name).read_text(encoding="utf-8")


@dataclass
class Web:
    """Pages by "host/path?query"; anything else is a 404. `resolve` maps hosts to addresses (public by default)."""

    pages: dict[str, tuple[int, str, dict[str, str]]] = field(default_factory=dict)
    addresses: dict[str, list[str]] = field(default_factory=dict)
    requests: list[httpx.Request] = field(default_factory=list)
    sleeps: list[float] = field(default_factory=list)

    def page(self, address: str, body: str, status: int = 200, **headers: str) -> Web:
        self.pages[address] = (status, body, headers)
        return self

    def file(self, address: str, name: str) -> Web:
        return self.page(address, recorded(name))

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        host = request.headers["host"]
        target = request.url.raw_path.decode()
        status, body, headers = self.pages.get(f"{host}{target}", (404, "Not found", {}))
        return httpx.Response(status, text=body, headers=headers)

    def resolve(self, host: str, port: int) -> list[str]:
        return self.addresses.get(host, [PUBLIC])

    def fetcher(self) -> Fetcher:
        client = httpx.Client(transport=httpx.MockTransport(self.handle), follow_redirects=False)
        return Fetcher(client, resolve=self.resolve, sleep=self.sleeps.append, clock=lambda: 0.0,
                       pacing=HostPacing(), robots=RobotsCache())  # fmt: skip

    def asked(self) -> list[str]:
        """The addresses requested, as "host/path?query"."""
        return [f"{r.headers['host']}{r.url.raw_path.decode()}" for r in self.requests]


def boards() -> Web:
    """Every recorded board, with the robots.txt rules each host had on 2026-10-22."""
    web = Web()
    web.page("boards-api.greenhouse.io/robots.txt", "User-agent: *\nDisallow: /embed/\n")
    web.file("boards-api.greenhouse.io/v1/boards/faire/jobs?content=true", "greenhouse_jobs.json")
    web.file("boards-api.greenhouse.io/v1/boards/faire/jobs/8821336002?pay_transparency=true", "greenhouse_job.json")
    web.page("api.lever.co/robots.txt", "User-agent: *\nAllow: /\nCrawl-delay: 1\n")
    web.file("api.lever.co/v0/postings/achievers?mode=json", "lever_postings.json")
    web.page("api.ashbyhq.com/robots.txt", "Unauthorized", status=401)
    web.file("api.ashbyhq.com/posting-api/job-board/cohere?includeCompensation=true", "ashby_board.json")
    web.file("api.smartrecruiters.com/robots.txt", "smartrecruiters_robots.txt")
    web.file("maplegrocers.ca/careers", "careers.html")
    web.file("maplegrocers.ca/careers/store-manager-toronto", "job_store_manager.html")
    web.file("maplegrocers.ca/careers/cashier-ottawa", "job_cashier.html")
    web.file("jobs.maplegrocers.ca/careers/buyer-vancouver", "job_buyer.html")
    web.file("maplegrocers.ca/careers/seasonal-clerk", "job_seasonal.html")
    web.file("maplegrocers.ca/careers/team-photo", "team_photo.html")
    web.file("www.faire.com/careers", "careers_embedded.html")
    return web


def smartrecruiters_allowed(web: Web) -> Web:
    """SmartRecruiters as it would answer if its robots.txt let us in."""
    web.page("api.smartrecruiters.com/robots.txt", "User-agent: *\nAllow: /\n")
    base = "api.smartrecruiters.com/v1/companies/NorthwindLogistics/postings"
    web.file(f"{base}?limit=100&offset=0", "smartrecruiters_postings_0.json")
    web.file(f"{base}?limit=100&offset=2", "smartrecruiters_postings_2.json")
    web.file(f"{base}/744000012345671", "smartrecruiters_posting.json")
    return web
