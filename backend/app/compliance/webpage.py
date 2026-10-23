"""The posting text of a fetched web page (PRD FR1, a posting's link).

Careers pages and ATS job boards mostly publish the posting as JSON-LD `JobPosting` data for search engines;
that is the posting without the page around it, so it is read first. Otherwise the page's main content is
read the way the extension reads a job editor: one line per list item with "• ", a heading on its own line,
a blank line between other blocks. Navigation, headers, footers, scripts and the application form (Greenhouse
and Lever put it under the posting) are left out.
"""

import html
import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from typing import Any

from app.compliance.money import parse_pay

MIN_POSTING_CHARS = 200  # less than this is a page that didn't render its posting without JavaScript

_BLOCKS = {
    "p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "section", "article", "main", "header",
    "footer", "blockquote", "table", "tr", "pre", "dl", "dt", "dd", "br", "hr",
}  # fmt: skip
_SKIP = {"script", "style", "template", "noscript", "svg", "iframe", "nav", "aside", "button", "select", "textarea", "head"}
_PAGE_CHROME = {"header", "footer"}  # left out of a whole page, kept inside the main content
_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
_UNITS = {"HOUR": "an hour", "DAY": "a day", "WEEK": "a week", "MONTH": "a month", "YEAR": "a year"}


@dataclass
class _Node:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list[_Node | str] = field(default_factory=list)


class _TreeBuilder(HTMLParser):
    """A forgiving tree: an end tag closes the nearest open element of its name, or nothing."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("#root")
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = _Node(tag, {name: value or "" for name, value in attrs})
        self.stack[-1].children.append(node)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack[-1].children.append(_Node(tag, {name: value or "" for name, value in attrs}))

    def handle_endtag(self, tag: str) -> None:
        for depth in range(len(self.stack) - 1, 0, -1):
            if self.stack[depth].tag == tag:
                del self.stack[depth:]
                return

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)


def _parse(markup: str) -> _Node:
    builder = _TreeBuilder()
    builder.feed(markup)
    builder.close()
    return builder.root


def _find_all(node: _Node, test: Any) -> list[_Node]:
    found = []
    for child in node.children:
        if isinstance(child, _Node):
            if test(child):
                found.append(child)
            found.extend(_find_all(child, test))
    return found


def _raw_text(node: _Node) -> str:
    return "".join(child if isinstance(child, str) else _raw_text(child) for child in node.children)


@dataclass
class _Line:
    text: str
    item: bool
    heading: bool


def _as_text(root: _Node, skip: set[str]) -> str:
    lines: list[_Line] = []
    current: _Line | None = None
    bullet = False

    def end() -> None:
        nonlocal current
        if current and (text := re.sub(r"\s+", " ", current.text).strip()):
            lines.append(_Line(text, current.item, current.heading))
        current = None

    def walk(node: _Node, in_item: bool, in_heading: bool) -> None:
        nonlocal current, bullet
        for child in node.children:
            if isinstance(child, str):
                if current is None:
                    if not child.strip():
                        continue
                    current = _Line("• " if bullet else "", in_item, in_heading)
                    bullet = False
                current.text += child
                continue
            if child.tag in skip or child.attrs.get("hidden") is not None or child.attrs.get("aria-hidden") == "true":
                continue
            block = child.tag in _BLOCKS
            if block:
                end()
            if child.tag == "li":
                bullet = True
            walk(child, in_item or child.tag == "li", in_heading or bool(re.fullmatch(r"h[1-6]", child.tag)))
            if block:
                end()

    walk(root, False, False)
    end()
    out = []
    for i, line in enumerate(lines):
        if i:
            previous = lines[i - 1]
            out.append("\n" if previous.heading or (previous.item and line.item) else "\n\n")
        out.append(line.text)
    return "".join(out).replace(" ", " ").strip()


def html_to_text(markup: str) -> str:
    """A fragment of HTML, such as a JSON-LD description, as posting text."""
    if "<" not in markup and "&lt;" in markup:  # escaped twice by the page
        markup = html.unescape(markup)
    return _as_text(_parse(markup), _SKIP)


# JSON-LD JobPosting


def _job_postings(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [posting for item in data for posting in _job_postings(item)]
    if not isinstance(data, dict):
        return []
    kind = data.get("@type")
    if kind == "JobPosting" or (isinstance(kind, list) and "JobPosting" in kind):
        return [data]
    return _job_postings(data.get("@graph", []))


def _first(value: Any) -> Any:
    return value[0] if isinstance(value, list) and value else value


def _name(value: Any) -> str | None:
    value = _first(value)
    if isinstance(value, dict):
        value = value.get("name")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _place(value: Any) -> str | None:
    value = _first(value)
    address = value.get("address") if isinstance(value, dict) else None
    if isinstance(address, str):
        return address.strip() or None
    if not isinstance(address, dict):
        return None
    parts = [address.get(key) for key in ("addressLocality", "addressRegion")]
    return ", ".join(part.strip() for part in parts if isinstance(part, str) and part.strip()) or None


def _amount(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value)) if value not in (None, "") else None
    except InvalidOperation:
        return None


def _money(amount: Decimal, currency: str) -> str:
    figure = f"{amount:,.0f}" if amount == amount.to_integral_value() else f"{amount:,.2f}"
    return f"${figure}" if currency == "CAD" else f"{currency} {figure}"


def _salary(value: Any) -> str | None:
    """schema.org baseSalary as a sentence, e.g. "Pay: $60,000 to $80,000 a year." """
    value = _first(value)
    if not isinstance(value, dict):
        return None
    currency = str(value.get("currency") or "CAD").upper()
    amount = value.get("value")
    unit = value.get("unitText") or (amount.get("unitText") if isinstance(amount, dict) else None)
    if isinstance(amount, dict):
        low, high = _amount(amount.get("minValue")), _amount(amount.get("maxValue"))
        low = low if low is not None else _amount(amount.get("value"))
    else:
        low, high = _amount(amount), None
    per = f" {_UNITS[str(unit).upper()]}" if str(unit).upper() in _UNITS else ""
    if low is not None and high is not None and high != low:
        return f"Pay: {_money(low, currency)} to {_money(high, currency)}{per}."
    single = low if low is not None else high
    return f"Pay: {_money(single, currency)}{per}." if single is not None else None


def _from_json_ld(root: _Node) -> str | None:
    scripts = _find_all(root, lambda n: n.tag == "script" and n.attrs.get("type", "").lower() == "application/ld+json")
    for script in scripts:
        try:
            data = json.loads(_raw_text(script))
        except ValueError:
            continue
        for posting in _job_postings(data):
            description = posting.get("description")
            body = html_to_text(description) if isinstance(description, str) else ""
            if len(body) < MIN_POSTING_CHARS:
                continue
            title = _name(posting.get("title"))
            where = " · ".join(filter(None, [_name(posting.get("hiringOrganization")), _place(posting.get("jobLocation"))]))
            # Pay shown beside the description (a header box many ATS pages draw from this data) is part of the
            # posting; it is added only when the description itself states no pay, so nothing is read twice.
            pay = _salary(posting.get("baseSalary")) if not parse_pay(body) else None
            return "\n\n".join(filter(None, [title, where, body, pay]))
    return None


def _from_page(root: _Node) -> str:
    def main_like(node: _Node) -> bool:
        return node.tag in ("main", "article") or node.attrs.get("role") == "main"

    candidates = _find_all(root, main_like)
    texts = [_as_text(node, _SKIP | {"form"}) for node in candidates]
    best = max(texts, key=len, default="")
    if len(best) >= MIN_POSTING_CHARS:
        return best
    body = next(iter(_find_all(root, lambda n: n.tag == "body")), root)
    text = _as_text(body, _SKIP | _PAGE_CHROME | {"form"})
    # Some sites (ASP.NET) wrap the whole page in one form: then read it, leaving out only its fields.
    return text if len(text) >= MIN_POSTING_CHARS else _as_text(body, _SKIP | _PAGE_CHROME)


def posting_text(markup: str) -> str:
    """The posting on a web page: its JSON-LD JobPosting, else its main content. Empty when there is little text."""
    root = _parse(markup)
    text = _from_json_ld(root) or _from_page(root)
    return text if len(text) >= MIN_POSTING_CHARS else ""
