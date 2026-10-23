"""Read a posting from its public link (PRD FR1), safely.

The server fetches a page someone else named, so every hop is checked before we connect: http or https on the
default port only, no user name or password in the link, no LinkedIn, Indeed or Glassdoor (PRD §10), and a host
whose every address is public. The connection then goes to the address that was checked, never to a second DNS
answer, so a host can't switch to a private address between the check and the connection. Redirects are
followed by hand and checked the same way. The page must be HTML or plain text, arrive within the time limit,
and stay under the size limit. When any of that fails, the user is asked to paste the posting instead.

The page is held in memory for the check only, like a pasted posting.
"""

import ipaddress
import re
import socket
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as ResolveTimeout
from dataclasses import dataclass

import httpx

from app.compliance.webpage import posting_text

MAX_REDIRECTS = 5
MAX_PAGE_BYTES = 2_000_000
DEADLINE_SECONDS = 15.0  # the whole fetch, redirects included
USER_AGENT = "Mozilla/5.0 (compatible; CheckON/1.0; +https://checkon.ca) posting check requested by a user"
TYPES = ("text/html", "application/xhtml+xml", "text/plain")
DEFAULT_PORTS = {"http": 80, "https": 443}

# PRD §10: we don't read these job sites, directly or through a redirect. SimplyHired is Indeed's.
BLOCKED_SITES = re.compile(
    r"(?:^|\.)(?:linkedin|indeed|glassdoor|simplyhired)\.(?:[a-z]{2,3}|co\.[a-z]{2}|com\.[a-z]{2})$|(?:^|\.)lnkd\.in$"
)

PASTE = "Paste the posting's text instead."
REFUSALS = {
    "bad_url": "Enter the posting's full web address, starting with https://.",
    "blocked_site": "CheckON doesn't read LinkedIn, Indeed or Glassdoor pages. Paste the posting's text instead, "
    "or check it with the CheckON browser extension while you view your posting there.",
    "unsafe_url": f"We can only read public web pages. {PASTE}",
    "fetch_failed": f"We couldn't open that page. {PASTE}",
    "not_a_page": f"That link isn't a web page we can read. {PASTE}",
    "no_posting": f"We couldn't find a job posting on that page. {PASTE}",
    "fetch_limit": "You've checked several links in a short time. Wait a while, or paste the posting's text instead.",
}


class LinkRefused(Exception):
    """The link can't be read. No check runs, and no credit is used."""

    def __init__(self, reason: str) -> None:
        super().__init__(REFUSALS[reason])
        self.reason = reason
        self.message = REFUSALS[reason]


@dataclass(frozen=True)
class FetchedPosting:
    url: str  # the page the posting was read from, after redirects
    text: str


Resolver = Callable[[str, int], list[str]]

_NAT64 = ipaddress.IPv6Network("64:ff9b::/96")
_resolver_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="resolve")


def system_resolver(host: str, port: int) -> list[str]:
    return [str(info[4][0]) for info in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)]


def is_public(address: str) -> bool:
    """A globally routable unicast address. IPv6 forms that carry an IPv4 address are judged by that address."""
    try:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address):
        nat64 = ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF) if ip in _NAT64 else None
        embedded = [ip.ipv4_mapped, ip.sixtofour, ip.teredo[1] if ip.teredo else None, nat64]
        if any(inner is not None and not is_public(str(inner)) for inner in embedded):
            return False
    return ip.is_global and not ip.is_multicast


def blocked_site(host: str) -> bool:
    return BLOCKED_SITES.search(host.lower().rstrip(".")) is not None


class LinkReader:
    """Fetches one posting page. `resolver` and `transport` are swapped in tests, which use no network."""

    def __init__(
        self,
        resolver: Resolver = system_resolver,
        transport: httpx.BaseTransport | None = None,
        deadline: float = DEADLINE_SECONDS,
        max_bytes: int = MAX_PAGE_BYTES,
    ) -> None:
        self.resolver = resolver
        self.transport = transport
        self.deadline = deadline
        self.max_bytes = max_bytes

    def read(self, link: str) -> FetchedPosting:
        url = self._parse(link)
        started = time.monotonic()
        with httpx.Client(
            transport=self.transport, follow_redirects=False, trust_env=False,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,text/plain;q=0.8"},
        ) as client:  # fmt: skip
            for _ in range(MAX_REDIRECTS + 1):
                addresses = self._addresses(url, started)
                response = self._connect(client, url, addresses, started)
                try:
                    if response.is_redirect and (location := response.headers.get("location")):
                        url = self._parse(str(url.join(location)))
                        continue
                    if response.status_code != 200:
                        raise LinkRefused("fetch_failed")
                    body = self._body(response, started)
                finally:
                    response.close()
                return FetchedPosting(url=str(url), text=self._text(response, body))
        raise LinkRefused("fetch_failed")  # too many redirects

    # Each hop

    def _parse(self, link: str) -> httpx.URL:
        try:
            url = httpx.URL(link.strip())
        except (httpx.InvalidURL, TypeError):
            raise LinkRefused("bad_url")
        if url.scheme not in DEFAULT_PORTS or not url.raw_host:
            raise LinkRefused("bad_url")
        host = url.raw_host.decode("ascii").lower().rstrip(".")
        if blocked_site(host):
            raise LinkRefused("blocked_site")
        if url.userinfo or url.port not in (None, DEFAULT_PORTS[url.scheme]):
            raise LinkRefused("unsafe_url")
        if "." not in host and ":" not in host:  # "localhost", or a name only a private network knows
            raise LinkRefused("unsafe_url")
        return url.copy_with(fragment=None)

    def _addresses(self, url: httpx.URL, started: float) -> list[str]:
        host = url.raw_host.decode("ascii").lower().rstrip(".")
        try:
            ipaddress.ip_address(host)
            addresses = [host]
        except ValueError:
            future = _resolver_pool.submit(self.resolver, host, DEFAULT_PORTS[url.scheme])
            try:
                addresses = future.result(timeout=self._left(started))
            except (OSError, ResolveTimeout):
                raise LinkRefused("fetch_failed")
        if not addresses:
            raise LinkRefused("fetch_failed")
        if not all(is_public(address) for address in addresses):  # one private answer is enough to refuse
            raise LinkRefused("unsafe_url")
        return sorted(dict.fromkeys(addresses), key=lambda address: ":" in address)  # IPv4 first

    def _connect(self, client: httpx.Client, url: httpx.URL, addresses: list[str], started: float) -> httpx.Response:
        """Connect to a checked address, keeping the host name for the Host header and the TLS certificate check."""
        host = url.raw_host.decode("ascii")
        for address in addresses[:2]:
            request = client.build_request(
                "GET", url.copy_with(host=address.split("%", 1)[0]), headers={"Host": host},
                timeout=self._timeout(started), extensions={"sni_hostname": host},
            )  # fmt: skip
            try:
                return client.send(request, stream=True)
            except httpx.ConnectError, httpx.ConnectTimeout:
                continue
            except httpx.HTTPError:
                raise LinkRefused("fetch_failed")
        raise LinkRefused("fetch_failed")

    def _body(self, response: httpx.Response, started: float) -> bytes:
        kind = response.headers.get("content-type", "text/html").split(";", 1)[0].strip().lower()
        if kind not in TYPES:
            raise LinkRefused("not_a_page")
        declared = response.headers.get("content-length", "")
        if declared.isdigit() and int(declared) > self.max_bytes:
            raise LinkRefused("not_a_page")
        chunks: list[bytes] = []
        size = 0
        try:
            for chunk in response.iter_bytes():  # decompressed, so the limit holds for a compressed page too
                size += len(chunk)
                if size > self.max_bytes:
                    raise LinkRefused("not_a_page")
                if self._left(started) <= 0:
                    raise LinkRefused("fetch_failed")
                chunks.append(chunk)
        except httpx.HTTPError:
            raise LinkRefused("fetch_failed")
        return b"".join(chunks)

    def _text(self, response: httpx.Response, body: bytes) -> str:
        charset = response.charset_encoding or "utf-8"
        try:
            page = body.decode(charset, errors="replace")
        except LookupError:
            page = body.decode("utf-8", errors="replace")
        kind = response.headers.get("content-type", "text/html").split(";", 1)[0].strip().lower()
        text = page.strip() if kind == "text/plain" else posting_text(page)
        if not text:
            raise LinkRefused("no_posting")
        return text

    def _left(self, started: float) -> float:
        return max(self.deadline - (time.monotonic() - started), 0.0)

    def _timeout(self, started: float) -> httpx.Timeout:
        return httpx.Timeout(min(5.0, max(self._left(started), 0.1)))
