"""HTML for careers page audits: a posting's HTML as the plain text applicants read, and from a careers page its
links, embedded scripts and schema.org JobPosting data (JSON-LD, the markup search engines read for job listings).
"""

import html
import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

_BLOCK = {
    "address", "article", "aside", "blockquote", "div", "dl", "fieldset", "figcaption", "figure", "footer", "form",
    "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "main", "nav", "ol", "p", "pre", "section", "table", "ul",
}  # fmt: skip
_LINE = {"br", "dd", "dt", "li", "tr"}  # a new line without a blank one
_SKIP = {"script", "style", "noscript", "template", "svg", "head", "button", "select", "iframe"}
_SPACES = re.compile(r"[ \t\r\f\v\u00a0]+")


@dataclass
class Page:
    text: str = ""
    title: str = ""
    site_name: str = ""  # og:site_name
    links: list[tuple[str, str]] = field(default_factory=list)  # (href, link text)
    sources: list[str] = field(default_factory=list)  # script and iframe src attributes
    json_ld: list[Any] = field(default_factory=list)


class _Reader(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.page = Page()
        self.lines: list[str] = []
        self.line: list[str] = []
        self.skipping = 0
        self.json_ld: list[str] | None = None
        self.in_title = False
        self.link: tuple[str, list[str]] | None = None

    def _break(self, blank: bool = True) -> None:
        line = _SPACES.sub(" ", "".join(self.line)).strip()
        if line:
            self.lines.append(line)
        if blank and self.lines and self.lines[-1]:
            self.lines.append("")
        self.line = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attrs}
        if tag in ("script", "iframe") and values.get("src"):
            self.page.sources.append(values["src"])
        if tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self.json_ld = []
        if tag == "meta" and values.get("property") == "og:site_name":
            self.page.site_name = values.get("content", "").strip()
        if tag == "title":
            self.in_title = True
        if tag == "a" and values.get("href"):
            self.link = (values["href"], [])
        if tag in _SKIP:
            self.skipping += 1
        elif tag in _BLOCK or tag in _LINE:
            self._break(blank=tag in _BLOCK)
            if tag == "li":
                self.line.append("• ")

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self.json_ld is not None:
            self.page.json_ld.extend(_json_ld("".join(self.json_ld)))
            self.json_ld = None
        if tag == "title":
            self.in_title = False
        if tag == "a" and self.link is not None:
            href, words = self.link
            self.page.links.append((href, _SPACES.sub(" ", "".join(words)).strip()))
            self.link = None
        if tag in _SKIP:
            self.skipping = max(self.skipping - 1, 0)
        elif tag in _BLOCK or tag in _LINE:
            self._break(blank=tag in _BLOCK)

    def handle_data(self, data: str) -> None:
        if self.json_ld is not None:
            self.json_ld.append(data)
        if self.in_title:
            self.page.title += data
        if self.skipping:
            return
        if self.link is not None:
            self.link[1].append(data)
        self.line.append(data.replace("\n", " "))

    def close(self) -> None:
        super().close()
        self._break()
        self.page.text = "\n".join(self.lines).strip()
        self.page.title = _SPACES.sub(" ", self.page.title).strip()


def _json_ld(raw: str) -> list[Any]:
    try:
        data = json.loads(raw.strip())
    except ValueError:
        return []
    return data if isinstance(data, list) else [data]


def read_page(markup: str) -> Page:
    reader = _Reader()
    reader.feed(markup)
    reader.close()
    return reader.page


def to_text(markup: str | None) -> str:
    """HTML as the text a reader sees: one line per block, list items as bullets, at most one blank line."""
    return read_page(markup).text if markup else ""


def unescaped(markup: str) -> str:
    """HTML that was escaped once more, as Greenhouse's job content is."""
    return html.unescape(markup)


# schema.org JobPosting


def job_postings(json_ld: list[Any]) -> list[dict[str, Any]]:
    """Every JobPosting in a page's JSON-LD, including ones inside @graph and ItemList entries."""
    found: list[dict[str, Any]] = []

    def visit(node: Any, depth: int = 0) -> None:
        if depth > 6:
            return
        if isinstance(node, list):
            for item in node:
                visit(item, depth + 1)
        elif isinstance(node, dict):
            kind = node.get("@type")
            kinds = kind if isinstance(kind, list) else [kind]
            if "JobPosting" in kinds:
                found.append(node)
                return
            for key in ("@graph", "itemListElement", "item", "mainEntity"):
                if key in node:
                    visit(node[key], depth + 1)

    visit(json_ld)
    return found


def _name(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("name") or "")
    return str(value or "")


def places(posting: dict[str, Any]) -> tuple[list[str], bool, str | None]:
    """A JobPosting's places as "City, Region, Country" lines, whether it's remote, and a country it names."""
    locations = posting.get("jobLocation") or []
    lines, country = [], None
    for location in locations if isinstance(locations, list) else [locations]:
        address = location.get("address") if isinstance(location, dict) else None
        if isinstance(address, dict):
            parts = [
                _name(address.get(key))
                for key in ("addressLocality", "addressRegion", "addressCountry")
            ]
            country = country or _name(address.get("addressCountry")) or None
            if line := ", ".join(part for part in parts if part):
                lines.append(line)
        elif isinstance(address, str) and address.strip():
            lines.append(address.strip())
    remote = str(posting.get("jobLocationType", "")).upper() == "TELECOMMUTE"
    required = posting.get("applicantLocationRequirements") or []
    for requirement in required if isinstance(required, list) else [required]:
        if name := _name(requirement):
            lines.append(name)
            country = country or name
    return lines, remote, country
