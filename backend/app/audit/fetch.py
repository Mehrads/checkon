"""Server-side fetches of public pages, for careers page audits. The customer types the address, so every fetch is
guarded against reaching our own network (SSRF):

- http or https on the default port only, with no user name or password in the address;
- the host must resolve to public addresses only (no private, loopback, link-local, shared, reserved or
  multicast ranges, IPv4 inside IPv6 included), and the connection goes to the address that was checked, so a
  second DNS answer can't swap it for an internal one;
- redirects are followed by hand, and each new address is checked the same way;
- responses are read up to a size cap, with timeouts, and without proxies from the environment.

The address checks are the posting link's (app/api/posting_link.py), so every server-side fetch refuses the same
addresses. Every fetch also obeys the site's robots.txt for our user agent (RFC 9309), including its Crawl-delay. Python's
urllib.robotparser isn't used: it applies the first rule that matches rather than the most specific one, and it
ignores * and $ in paths, so a robots.txt that starts with "Allow: /" would let us read everything.
"""

import json
import re
import socket
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import unquote

import httpx

from app.api.posting_link import is_public

USER_AGENT = "CheckON/1.0 (+https://github.com/Mehrads/checkon)"
ROBOTS_AGENT = "CheckON"  # the name robots.txt rules are matched against
MAX_BYTES = 16_000_000  # a big job board's JSON; pages are far smaller
ROBOTS_MAX_BYTES = 500_000  # RFC 9309 asks crawlers to read at least 500 KiB
ROBOTS_TTL = 3600.0  # seconds a robots.txt answer is reused
MAX_REDIRECTS = 5
MAX_CRAWL_DELAY = 10.0  # seconds; a longer Crawl-delay is refused rather than waited out
TIMEOUT = httpx.Timeout(10.0, read=20.0)

Resolve = Callable[[str, int], list[str]]


class FetchError(Exception):
    """A fetch that failed, with a message for the customer."""


class Blocked(FetchError):
    """The address isn't a public web page we may fetch."""


class RobotsRefused(FetchError):
    """The site's robots.txt doesn't let us read this address."""


class Unavailable(FetchError):
    """A 4xx answer, or LinkedIn's 999: the page isn't there, or isn't open to us."""

    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.status = status


def resolve(host: str, port: int) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise FetchError(f"We couldn't find {host}. Check the address.")
    return sorted({str(info[4][0]) for info in infos})


def public_address(address: str) -> bool:
    """A globally reachable unicast address, IPv4 inside IPv6 included: the posting link's check."""
    return is_public(address)


def checked_url(url: str | httpx.URL) -> httpx.URL:
    """The address if it may be fetched at all, before any DNS lookup."""
    try:
        parsed = httpx.URL(url)
    except httpx.InvalidURL, TypeError:
        raise Blocked("That doesn't look like a web address.")
    if parsed.scheme not in ("http", "https") or not parsed.host:
        raise Blocked("Enter a web address that starts with https://.")
    if parsed.userinfo:
        raise Blocked("Enter the address without a user name or password.")
    if parsed.port is not None:
        raise Blocked("Enter the address without a port number.")
    if "." not in parsed.host and ":" not in parsed.host:  # "localhost", or a name only a private network knows
        raise Blocked("That address isn't a public web page.")
    return parsed


@dataclass
class Robots:
    """A site's robots.txt rules for our user agent: (allow, path pattern) pairs, and its Crawl-delay."""

    rules: list[tuple[bool, str]] = field(default_factory=list)
    crawl_delay: float | None = None

    def allows(self, target: str) -> bool:
        """The most specific matching rule decides (the longest pattern); Allow wins a tie (RFC 9309, 2.2.2)."""
        path = unquote(target)
        if path == "/robots.txt":
            return True
        best: tuple[int, bool] | None = None
        for allow, pattern in self.rules:
            if pattern and _pattern(pattern).match(path):
                if best is None or len(pattern) > best[0] or (len(pattern) == best[0] and allow):
                    best = (len(pattern), allow)
        return best is None or best[1]


def _pattern(pattern: str) -> re.Pattern[str]:
    """A robots.txt path pattern: * is any run of characters, a final $ anchors the end."""
    anchored = pattern.endswith("$")
    body = ".*".join(re.escape(part) for part in unquote(pattern.removesuffix("$")).split("*"))
    return re.compile(body + ("$" if anchored else ""), re.DOTALL)


def parse_robots(text: str, agent: str = ROBOTS_AGENT) -> Robots:
    """The rules of every group naming `agent` (case-insensitively), combined; failing that, the * groups'."""
    groups: list[tuple[set[str], list[tuple[bool, str]], list[float]]] = []
    in_agents = False
    for raw in text.lstrip("\ufeff").splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if not in_agents:
                groups.append((set(), [], []))
            groups[-1][0].add(value.split("/")[0].strip().lower())
            in_agents = True
            continue
        if not groups:
            continue  # rules before any user-agent line belong to no group
        in_agents = False
        if key in ("allow", "disallow"):
            groups[-1][1].append((key == "allow", value))
        elif key == "crawl-delay":
            try:
                groups[-1][2].append(float(value))
            except ValueError:
                pass
    mine = [g for g in groups if agent.lower() in g[0]] or [g for g in groups if "*" in g[0]]
    delays = [delay for g in mine for delay in g[2]]
    return Robots([rule for g in mine for rule in g[1]], delays[0] if delays else None)


class HostPacing:
    """When each host may be fetched next, for robots.txt Crawl-delay. Shared by every audit in this process."""

    def __init__(self) -> None:
        self._next: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, host: str, delay: float, now: float) -> float:
        """Seconds to wait before fetching from `host`; books the slot after it."""
        with self._lock:
            start = max(now, self._next.get(host, 0.0))
            self._next[host] = start + delay
            return start - now


class RobotsCache:
    """Each site's robots.txt rules for an hour, shared by every audit in this process."""

    def __init__(self) -> None:
        self._rules: dict[str, tuple[float, Robots]] = {}
        self._lock = threading.Lock()

    def get(self, origin: str, now: float) -> Robots | None:
        with self._lock:
            found = self._rules.get(origin)
            return found[1] if found and found[0] > now else None

    def put(self, origin: str, rules: Robots, now: float) -> None:
        with self._lock:
            self._rules = {key: value for key, value in self._rules.items() if value[0] > now}
            self._rules[origin] = (now + ROBOTS_TTL, rules)


_pacing = HostPacing()
_robots = RobotsCache()


class Fetcher:
    """Guarded fetches. Tests swap out the HTTP client, DNS, the clock and the shared caches."""

    def __init__(
        self, client: httpx.Client | None = None, resolve: Resolve = resolve,
        sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic,
        pacing: HostPacing = _pacing, robots: RobotsCache = _robots,
    ) -> None:  # fmt: skip
        self.client = client or httpx.Client(timeout=TIMEOUT, trust_env=False, follow_redirects=False)
        self.resolve = resolve
        self.sleep = sleep
        self.clock = clock
        self.pacing = pacing
        self.robots = robots

    def content(self, url: str, max_bytes: int = MAX_BYTES) -> tuple[bytes, httpx.URL]:
        """The body of a file the site's robots.txt lets us read, and its address after redirects."""
        return self._get(checked_url(url), max_bytes, robots=True)

    def text(self, url: str, max_bytes: int = MAX_BYTES) -> tuple[str, httpx.URL]:
        """The body of a page the site's robots.txt lets us read, and its address after redirects."""
        body, final = self.content(url, max_bytes)
        return body.decode("utf-8", errors="replace"), final

    def json(self, url: str, max_bytes: int = MAX_BYTES) -> object:
        body, _ = self._get(checked_url(url), max_bytes, robots=True)
        try:
            return json.loads(body)
        except ValueError:
            raise FetchError("The job board sent something we couldn't read. Try again later.")

    # robots.txt

    def _rules(self, url: httpx.URL) -> Robots:
        origin = f"{url.scheme}://{url.host}"
        if (rules := self.robots.get(origin, self.clock())) is None:
            try:
                body, _ = self._get(httpx.URL(f"{origin}/robots.txt"), ROBOTS_MAX_BYTES, robots=False)
                rules = parse_robots(body.decode("utf-8", errors="replace"))
            except Blocked:
                raise
            except Unavailable as error:  # 4xx: no rules (RFC 9309, 2.3.1.3); rate limited or refused: no reading
                rules = Robots([(False, "/")]) if error.status in (429, 999) else Robots()
            except FetchError:  # unreachable or 5xx: assume everything is disallowed (2.3.1.4)
                rules = Robots([(False, "/")])
            self.robots.put(origin, rules, self.clock())
        return rules

    def _allowed(self, url: httpx.URL) -> None:
        rules = self._rules(url)
        if not rules.allows(url.raw_path.decode("ascii")):
            raise RobotsRefused(f"{url.host} asks automated readers not to read {url.path} (its robots.txt).")
        delay = rules.crawl_delay or 0.0
        if delay > MAX_CRAWL_DELAY:
            raise RobotsRefused(f"{url.host} asks automated readers to wait {delay:.0f} seconds between pages.")
        if delay and (wait := self.pacing.wait(url.host, delay, self.clock())) > 0:
            self.sleep(wait)

    # The guarded request

    def _address(self, url: httpx.URL) -> str:
        port = url.port or (443 if url.scheme == "https" else 80)
        addresses = self.resolve(url.host, port)
        if not addresses or not all(public_address(address) for address in addresses):
            raise Blocked("That address isn't a public web page.")
        return addresses[0]

    def _get(self, url: httpx.URL, max_bytes: int, robots: bool) -> tuple[bytes, httpx.URL]:
        for _ in range(MAX_REDIRECTS + 1):
            checked_url(url)
            address = self._address(url)
            if robots:
                self._allowed(url)
            request = self.client.build_request(
                "GET", url.copy_with(host=address),  # connect to the address that was checked
                headers={"Host": url.netloc.decode("ascii"), "User-Agent": USER_AGENT,
                         "Accept": "application/json, text/html;q=0.9, */*;q=0.5"},
                extensions={"sni_hostname": url.host} if url.scheme == "https" else {},
            )  # fmt: skip
            try:
                response = self.client.send(request, stream=True)
            except httpx.HTTPError:
                raise FetchError(f"We couldn't reach {url.host}. Try again later.")
            try:
                if response.is_redirect and (location := response.headers.get("location")):
                    url = url.join(location)
                    continue
                if response.status_code in (401, 403, 429, 999):  # 999: LinkedIn's answer to automated readers
                    raise Unavailable(
                        f"{url.host} blocks automated readers ({response.status_code}), so we can't read it.",
                        response.status_code,
                    )
                if 400 <= response.status_code < 500:
                    raise Unavailable(f"{url.host} answered {response.status_code} for that address.", response.status_code)
                if response.status_code >= 300:
                    raise FetchError(f"{url.host} isn't answering properly right now. Try again later.")
                return _read(response, max_bytes, url), url
            finally:
                response.close()
        raise FetchError(f"{url.host} redirected too many times.")


def _read(response: httpx.Response, max_bytes: int, url: httpx.URL) -> bytes:
    body = bytearray()
    try:
        for chunk in response.iter_bytes():
            body.extend(chunk)
            if len(body) > max_bytes:
                raise FetchError(f"The page at {url.host} is too large to read.")
    except httpx.HTTPError:
        raise FetchError(f"We couldn't read the page at {url.host}. Try again later.")
    return bytes(body)
