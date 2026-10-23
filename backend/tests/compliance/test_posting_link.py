"""Reading a posting from its link, with no network: a scripted resolver and a mock transport. Every hop is
checked before connecting: scheme, port, blocked job sites, and a public address for the host."""

import time
from collections.abc import Callable

import httpx
import pytest

from app.api.posting_link import LinkReader, LinkRefused, blocked_site, is_public

POSTING_HTML = """<html><head><title>Payroll Specialist</title></head><body>
<nav>Home · Careers · Contact</nav>
<main><h1>Payroll Specialist</h1>
<p>We're growing. You'll run payroll for 400 employees across Ontario, working with our finance team.</p>
<h2>Requirements</h2><ul><li>2+ years of payroll experience</li><li>Excellent communication skills</li></ul>
<p>Salary: $60,000 – $80,000 per year. This posting is for an existing vacancy.</p></main>
<footer>© Example Inc.</footer></body></html>"""

DNS = {"jobs.example.com": ["93.184.216.34"], "careers.example.org": ["93.184.216.35", "2606:2800:220:1::35"]}


def resolver(table: dict[str, list[str]]) -> Callable[[str, int], list[str]]:
    def resolve(host: str, _port: int) -> list[str]:
        if host not in table:
            raise OSError("no such host")
        return table[host]

    return resolve


class Server:
    """Answers by host name (the Host header) and path; records every request it was sent."""

    def __init__(self, routes: dict[str, httpx.Response | Callable[[httpx.Request], httpx.Response]]) -> None:
        self.routes = routes
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        route = self.routes.get(f"{request.headers['host']}{request.url.path}")
        if route is None:
            return httpx.Response(404)
        return route(request) if callable(route) else route


def page(body: str = POSTING_HTML, content_type: str = "text/html; charset=utf-8", **headers: str) -> httpx.Response:
    return httpx.Response(200, headers={"content-type": content_type, **headers}, text=body)


def redirect(to: str, status: int = 302) -> httpx.Response:
    return httpx.Response(status, headers={"location": to})


def reader(server: Server, table: dict[str, list[str]] = DNS, **options: float) -> LinkReader:
    return LinkReader(resolver=resolver(table), transport=httpx.MockTransport(server), **options)  # type: ignore[arg-type]


def refusal(link: str, server: Server | None = None, table: dict[str, list[str]] = DNS, **options: float) -> str:
    with pytest.raises(LinkRefused) as error:
        reader(server or Server({}), table, **options).read(link)
    return error.value.reason


def test_reads_the_posting_and_connects_to_the_checked_address() -> None:
    server = Server({"jobs.example.com/payroll": page()})
    fetched = reader(server).read("https://jobs.example.com/payroll#apply")
    assert fetched.url == "https://jobs.example.com/payroll" and not fetched.redirected
    assert fetched.text.startswith("Payroll Specialist\n")
    assert "• 2+ years of payroll experience\n• Excellent communication skills" in fetched.text
    assert "Home · Careers" not in fetched.text and "© Example" not in fetched.text
    [request] = server.requests
    # Pinned: the connection goes to the address that was checked, with the host name kept for the Host header
    # and for TLS (SNI and the certificate check).
    assert request.url.host == "93.184.216.34"
    assert request.headers["host"] == "jobs.example.com"
    assert request.extensions["sni_hostname"] == "jobs.example.com"
    assert "CheckON" in request.headers["user-agent"]


@pytest.mark.parametrize(
    "link",
    ["file:///etc/passwd", "ftp://jobs.example.com/posting.txt", "gopher://jobs.example.com:70/", "javascript:alert(1)",
     "data:text/html,<p>posting</p>", "jobs.example.com/payroll", "https://", "not a link"],
)  # fmt: skip
def test_only_http_and_https_links_are_read(link: str) -> None:
    server = Server({})
    assert refusal(link, server) == "bad_url"
    assert server.requests == []


@pytest.mark.parametrize(
    "link",
    [
        "http://127.0.0.1/", "http://10.0.0.5/admin", "http://172.16.0.1/", "http://192.168.1.1/",
        "http://169.254.169.254/latest/meta-data/", "http://0.0.0.0/", "http://100.64.0.1/", "http://[::1]/",
        "http://[::ffff:127.0.0.1]/", "http://[fd00::1]/", "http://[fe80::1]/", "http://224.0.0.1/",
        "http://localhost/", "http://intranet/", "http://2130706433/", "https://user:secret@jobs.example.com/",
        "http://jobs.example.com:8080/", "https://jobs.example.com:22/",
    ],
)  # fmt: skip
def test_private_addresses_odd_ports_and_credentials_are_refused(link: str) -> None:
    server = Server({})
    assert refusal(link, server) == "unsafe_url"
    assert server.requests == []


@pytest.mark.parametrize(
    "answers",
    [["10.0.0.1"], ["93.184.216.34", "10.0.0.1"], ["127.0.0.1"], ["169.254.169.254"], ["::1"], ["fd12::7"],
     ["::ffff:192.168.0.10"], ["2002:0a00:0001::1"], ["64:ff9b::a00:1"]],
)  # fmt: skip
def test_a_host_with_any_private_address_is_refused(answers: list[str]) -> None:
    """DNS rebinding and split answers: one private address is enough, and nothing is fetched."""
    server = Server({"rebind.example.net/": page()})
    assert refusal("https://rebind.example.net/", server, {"rebind.example.net": answers}) == "unsafe_url"
    assert server.requests == []


def test_a_name_that_spells_a_private_address_is_refused() -> None:
    """getaddrinfo reads 0x7f.0.0.1 as 127.0.0.1; the answer is checked, not the spelling."""
    assert refusal("http://0x7f.0.0.1/", table={"0x7f.0.0.1": ["127.0.0.1"]}) == "unsafe_url"


@pytest.mark.parametrize(
    "target",
    ["http://169.254.169.254/latest/meta-data/", "http://127.0.0.1:80/", "http://internal.example.com/",
     "http://[::1]/", "https://jobs.example.com:8443/", "file:///etc/passwd"],
)  # fmt: skip
def test_redirects_are_checked_like_the_first_link(target: str) -> None:
    server = Server({"jobs.example.com/payroll": redirect(target)})
    table = {**DNS, "internal.example.com": ["10.1.2.3"]}
    assert refusal("https://jobs.example.com/payroll", server, table) in ("unsafe_url", "bad_url")
    assert len(server.requests) == 1  # the redirect's target is never contacted


def test_redirects_to_public_pages_are_followed_and_pinned_again() -> None:
    server = Server({
        "jobs.example.com/old": redirect("https://careers.example.org/payroll", 301),
        "careers.example.org/payroll": page(),
    })  # fmt: skip
    fetched = reader(server).read("http://jobs.example.com/old")
    assert fetched.url == "https://careers.example.org/payroll" and fetched.redirected
    assert [(r.url.host, r.headers["host"]) for r in server.requests] == [
        ("93.184.216.34", "jobs.example.com"),
        ("93.184.216.35", "careers.example.org"),  # IPv4 first
    ]


def test_a_relative_redirect_stays_on_the_host() -> None:
    server = Server({"jobs.example.com/a": redirect("/b"), "jobs.example.com/b": page()})
    assert reader(server).read("https://jobs.example.com/a").url == "https://jobs.example.com/b"


def test_too_many_redirects_fail() -> None:
    server = Server({"jobs.example.com/loop": redirect("/loop")})
    assert refusal("https://jobs.example.com/loop", server) == "fetch_failed"
    assert len(server.requests) == 6


@pytest.mark.parametrize(
    "link",
    [
        "https://www.linkedin.com/jobs/view/123", "https://ca.linkedin.com/jobs/view/123", "https://linkedin.com/x",
        "https://lnkd.in/abc", "https://ca.indeed.com/viewjob?jk=1", "https://www.indeed.com/viewjob?jk=1",
        "https://indeed.ca/job", "https://uk.indeed.co.uk/x", "https://www.glassdoor.ca/job-listing/x",
        "https://glassdoor.com/x", "https://www.glassdoor.co.uk/x", "https://WWW.LinkedIn.COM./jobs",
        "https://www.simplyhired.ca/job/x", "http://www.linkedin.com:8080/x",
    ],
)  # fmt: skip
def test_linkedin_indeed_and_glassdoor_are_not_read(link: str) -> None:
    server = Server({})
    assert refusal(link, server) == "blocked_site"
    assert server.requests == []


def test_a_redirect_to_a_blocked_site_is_refused() -> None:
    server = Server({"jobs.example.com/apply": redirect("https://www.linkedin.com/jobs/view/123")})
    assert refusal("https://jobs.example.com/apply", server) == "blocked_site"
    assert len(server.requests) == 1


@pytest.mark.parametrize("host", ["indeed.mycompany.com", "careers.linkedinlearning.example", "glassdoorsinc.ca", "jobs.example.com"])
def test_other_sites_with_similar_names_are_not_blocked(host: str) -> None:
    assert not blocked_site(host)


@pytest.mark.parametrize(
    ("address", "public"),
    [("93.184.216.34", True), ("2606:2800:220:1::35", True), ("8.8.8.8", True), ("10.0.0.1", False),
     ("192.0.2.1", False), ("198.18.0.1", False), ("255.255.255.255", False), ("::", False),
     ("2001:db8::1", False), ("::ffff:8.8.8.8", True), ("fe80::1%en0", False), ("not an address", False)],
)  # fmt: skip
def test_is_public(address: str, public: bool) -> None:
    assert is_public(address) is public


def test_unknown_hosts_and_errors_fail() -> None:
    assert refusal("https://nowhere.example.com/") == "fetch_failed"
    assert refusal("https://jobs.example.com/missing", Server({})) == "fetch_failed"  # 404
    server = Server({"jobs.example.com/down": httpx.Response(503)})
    assert refusal("https://jobs.example.com/down", server) == "fetch_failed"


def test_a_slow_server_fails() -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    assert refusal("https://jobs.example.com/slow", Server({"jobs.example.com/slow": timeout})) == "fetch_failed"


def test_a_slow_resolver_fails_within_the_deadline() -> None:
    def slow(_host: str, _port: int) -> list[str]:
        time.sleep(1)
        return ["93.184.216.34"]

    started = time.monotonic()
    with pytest.raises(LinkRefused) as error:
        LinkReader(resolver=slow, transport=httpx.MockTransport(Server({})), deadline=0.2).read("https://slow.example.com/")
    assert error.value.reason == "fetch_failed"
    assert time.monotonic() - started < 0.9


def test_the_second_address_is_tried_when_the_first_does_not_connect() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "93.184.216.35":
            raise httpx.ConnectError("unreachable", request=request)
        return page()

    fetched = LinkReader(resolver=resolver(DNS), transport=httpx.MockTransport(handler)).read("https://careers.example.org/")
    assert "Payroll Specialist" in fetched.text


def test_pages_over_the_size_limit_are_refused() -> None:
    big = page("<main>" + "<p>Payroll duties and more payroll duties.</p>" * 200 + "</main>")
    assert refusal("https://jobs.example.com/big", Server({"jobs.example.com/big": big}), max_bytes=5000) == "not_a_page"
    declared = page(**{"content-length": "999999999"})
    assert refusal("https://jobs.example.com/d", Server({"jobs.example.com/d": declared})) == "not_a_page"


def test_only_web_pages_and_plain_text_are_read() -> None:
    pdf = httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF-1.7")
    assert refusal("https://jobs.example.com/p.pdf", Server({"jobs.example.com/p.pdf": pdf})) == "not_a_page"
    plain = page("Payroll Specialist\nSalary: $60,000 - $80,000 per year.", "text/plain")
    assert reader(Server({"jobs.example.com/t": plain})).read("https://jobs.example.com/t").text.startswith("Payroll")


def test_a_page_with_no_posting_text_asks_for_a_paste() -> None:
    app_shell = page("<html><body><div id='root'></div><script>render()</script></body></html>")
    assert refusal("https://jobs.example.com/spa", Server({"jobs.example.com/spa": app_shell})) == "no_posting"


def test_every_refusal_asks_for_the_text_instead() -> None:
    from app.api.posting_link import REFUSALS

    for reason, message in REFUSALS.items():
        if reason != "bad_url":
            assert "Paste the posting" in message or "paste the posting" in message, reason
