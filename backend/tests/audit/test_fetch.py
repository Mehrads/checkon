"""The guarded fetcher: no address inside our network, by any route (DNS, IPv6 forms, redirects), robots.txt
obeyed, and responses capped. No network: the web and DNS are fakes."""

import pytest

from app.audit.fetch import (
    Blocked,
    FetchError,
    RobotsRefused,
    Unavailable,
    checked_url,
    parse_robots,
    public_address,
)
from tests.audit.web import PUBLIC, Web


@pytest.mark.parametrize("address", [
    "10.0.0.5", "172.16.0.1", "192.168.1.1", "127.0.0.1", "0.0.0.0", "169.254.169.254", "100.64.0.1", "224.0.0.1",
    "::1", "fc00::1", "fe80::1", "::ffff:10.0.0.5", "::ffff:127.0.0.1", "64:ff9b::a00:5", "2002:a00:5::",
    "2001:0:4136:e378:8000:63bf:f5ff:fffa",  # Teredo carrying 10.0.0.5
])  # fmt: skip
def test_internal_addresses_are_refused(address: str) -> None:
    assert not public_address(address)


@pytest.mark.parametrize("address", ["93.184.216.34", "2606:4700::6812:101", "::ffff:93.184.216.34"])
def test_public_addresses_are_allowed(address: str) -> None:
    assert public_address(address)


@pytest.mark.parametrize("url", [
    "ftp://example.com/jobs", "file:///etc/passwd", "https://user:secret@example.com/", "https://example.com:8443/",
    "http://example.com:6379/", "javascript:alert(1)", "https:///jobs",
])  # fmt: skip
def test_only_plain_web_addresses(url: str) -> None:
    with pytest.raises(Blocked):
        checked_url(url)


def test_a_host_that_resolves_inside_our_network_is_refused() -> None:
    web = Web(addresses={"metadata.example": ["169.254.169.254"], "mixed.example": [PUBLIC, "10.0.0.5"]})
    for host in ("metadata.example", "mixed.example"):
        with pytest.raises(Blocked):
            web.fetcher().text(f"https://{host}/careers")
    assert web.requests == []  # not even its robots.txt


def test_a_redirect_into_our_network_is_refused() -> None:
    web = Web(addresses={"internal.example": ["10.0.0.5"]})
    web.page("careers.example/jobs", "", status=302, location="https://internal.example/admin")
    web.page("careers.example/old", "", status=301, location="http://localhost/")
    web.addresses["localhost"] = ["127.0.0.1"]
    with pytest.raises(Blocked):
        web.fetcher().text("https://careers.example/jobs")
    with pytest.raises(Blocked):
        web.fetcher().text("https://careers.example/old")
    assert "internal.example/admin" not in web.asked() and "localhost/" not in web.asked()


def test_the_connection_goes_to_the_checked_address() -> None:
    web = Web().page("careers.example/jobs", "<p>Jobs</p>")
    text, final = web.fetcher().text("https://careers.example/jobs")
    assert (text, str(final)) == ("<p>Jobs</p>", "https://careers.example/jobs")
    request = web.requests[-1]
    assert request.url.host == PUBLIC  # not looked up again by the HTTP client
    assert request.headers["host"] == "careers.example"
    assert request.extensions["sni_hostname"] == "careers.example"  # the certificate is checked for the name
    assert request.headers["user-agent"].startswith("CheckON/")


def test_redirects_are_followed_a_few_times() -> None:
    web = Web().page("a.example/1", "", status=301, location="/2").page("a.example/2", "done")
    assert web.fetcher().text("https://a.example/1")[0] == "done"
    loop = Web()
    for n in range(10):
        loop.page(f"a.example/{n}", "", status=302, location=f"/{n + 1}")
    with pytest.raises(FetchError, match="redirected too many times"):
        loop.fetcher().text("https://a.example/0")


def test_robots_txt_is_obeyed() -> None:
    web = Web().page("a.example/robots.txt", "User-agent: *\nDisallow: /private/\n\nUser-agent: CheckON\nDisallow: /jobs/x")
    web.page("a.example/jobs/y", "ok").page("a.example/private/z", "secret")
    fetcher = web.fetcher()
    assert fetcher.text("https://a.example/jobs/y")[0] == "ok"
    with pytest.raises(RobotsRefused):
        fetcher.text("https://a.example/jobs/x")
    with pytest.raises(RobotsRefused):
        Web().page("a.example/robots.txt", "User-agent: *\nDisallow: /\n").fetcher().text("https://a.example/jobs/y")
    assert web.asked().count("a.example/robots.txt") == 1  # read once and kept


INDEED_LIKE = """User-agent: *
Allow: /
Disallow: /job/
Disallow: /viewjob
Disallow: /cmp/*/people
Allow: /cmp/*/people/public$
Disallow: /*?from=
Crawl-delay: 1

User-agent: Googlebot
Allow: /job/
"""


@pytest.mark.parametrize(("path", "allowed"), [
    ("/", True), ("/cmp/Acme/jobs", True), ("/job/x", False), ("/viewjob?jk=1", False),
    ("/cmp/Acme/people", False), ("/cmp/Acme/people/public", True), ("/cmp/Acme/people/public/2", False),
    ("/jobs?from=home", False), ("/jobs?q=payroll&from=home", True), ("/robots.txt", True),
])  # fmt: skip
def test_robots_rules_the_most_specific_match_wins(path: str, allowed: bool) -> None:
    """"Allow: /" first doesn't open everything: the longest matching pattern decides, with * and $ (RFC 9309)."""
    assert parse_robots(INDEED_LIKE).allows(path) is allowed


def test_robots_groups() -> None:
    assert parse_robots(INDEED_LIKE).crawl_delay == 1.0
    assert parse_robots(INDEED_LIKE, agent="Googlebot").allows("/job/x")  # its own group, not *'s
    ours = parse_robots("User-agent: *\nDisallow: /\n\nUser-agent: other\nUser-agent: checkon/2.0\nAllow: /jobs\n")
    assert ours.allows("/jobs/1") and ours.allows("/about")  # a group naming us replaces *'s "Disallow: /"
    assert parse_robots("Disallow: /\n").allows("/x")  # a rule outside any group applies to no one
    assert parse_robots("User-agent: *\nDisallow:\n").allows("/x")  # an empty Disallow allows everything


def test_a_site_that_blocks_automated_readers() -> None:
    web = Web().page("a.example/jobs", "Verify you are human", status=403).page("b.example/robots.txt", "", status=429)
    with pytest.raises(Unavailable, match="blocks automated readers"):
        web.fetcher().text("https://a.example/jobs")
    with pytest.raises(RobotsRefused):  # rate limited on robots.txt: read nothing
        web.fetcher().text("https://b.example/jobs")


def test_robots_txt_that_is_missing_or_failing() -> None:
    missing = Web().page("a.example/jobs", "ok")  # robots.txt 404: no rules
    assert missing.fetcher().text("https://a.example/jobs")[0] == "ok"
    failing = Web().page("a.example/robots.txt", "down", status=503).page("a.example/jobs", "ok")
    with pytest.raises(RobotsRefused):  # a server error: assume everything is disallowed
        failing.fetcher().text("https://a.example/jobs")


def test_crawl_delay_spaces_out_requests() -> None:
    web = Web().page("a.example/robots.txt", "User-agent: *\nCrawl-delay: 2\n").page("a.example/1", "1")
    fetcher = web.fetcher()
    fetcher.text("https://a.example/1")
    fetcher.text("https://a.example/1")
    assert web.sleeps == [2.0]  # the clock stands still, so the second request waits the whole delay
    slow = Web().page("a.example/robots.txt", "User-agent: *\nCrawl-delay: 60\n")
    with pytest.raises(RobotsRefused, match="wait 60 seconds"):
        slow.fetcher().text("https://a.example/1")


def test_pages_have_a_size_cap_and_errors_have_messages() -> None:
    web = Web().page("a.example/big", "x" * 2000).page("a.example/gone", "", status=404)
    web.page("a.example/broken", "oops", status=500)
    with pytest.raises(FetchError, match="too large"):
        web.fetcher().text("https://a.example/big", max_bytes=1000)
    with pytest.raises(Unavailable):
        web.fetcher().text("https://a.example/gone")
    with pytest.raises(FetchError, match="isn't answering"):
        web.fetcher().text("https://a.example/broken")
