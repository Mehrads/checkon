"""A posting's application form, read from its job board for a careers page audit: ESA s. 8.3 (1) bars Canadian
experience requirements "in the posting or in any associated application form", so the audit checks the form too.

The form comes back as the text the form check reads (app/compliance/form.py): one question per line, " *" after a
required question and " (optional)" after one applicants may skip, and its answer options on the lines after it, each
starting with "- ". Only the questions the employer added are read. The fields the board puts on every form (name,
email, phone, location, résumé and cover letter; on Lever also current company and profile links) and the voluntary
self-identification surveys (gender, race, disability, veteran status) never ask about experience, so they're left
out; a form that asks nothing else comes back as an empty text.

- Greenhouse: the job board API lists the form's questions with ?questions=true.
- Lever: the postings API leaves the form out. The posting's apply page carries each card of the employer's questions
  as JSON, in the hidden field the form sends back with the application.
- Ashby: the posting API leaves the form out, and the board page reads it from Ashby's GraphQL API under
  jobs.ashbyhq.com/api/, which that site's robots.txt asks crawlers not to read (October 2026). Not read.
- SmartRecruiters: its API's robots.txt refuses every crawler but LinkedIn's. Not read.
- A careers page: its own form, when it has one, has no common markup to read reliably. Not read; the customer pastes
  it, or the extension reads it from the page.

Fetch failures raise FetchError, as posting_text's do; None is a form we don't or can't read.
"""

import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, cast
from urllib.parse import quote

from app.audit.boards import MAX_PAGE_BYTES, Source
from app.audit.fetch import Fetcher, FetchError

MAX_OPTIONS = 25  # answer options listed per question; a longer pick list (countries, schools) is cut short


def application_form(source: Source, key: str, posting: str, fetcher: Fetcher) -> str | None:
    """The questions on a posting's application form, as the form check reads them; None when we don't read the
    board's forms, or couldn't read this one. `key` and `posting` are the board's and the posting's ids (Board.key,
    Found.id)."""
    if source == "greenhouse":
        return _greenhouse(key, posting, fetcher)
    if source == "lever":
        return _lever(key, posting, fetcher)
    return None


@dataclass
class _Question:
    label: str
    required: bool | None  # None when the board doesn't say
    options: list[str]


_MARKS = re.compile(r"(?:\s*(?:\*+|[(\[](?:required|mandatory|optional)[)\]]))+$", re.IGNORECASE)
_BULLET = re.compile(r"^(?:[-•·▪◦‣○●■□☐➢➤*]|\(\s?\)|\[\s?\])+\s*")
_LETTERED = re.compile(r"^[a-z][.)]")  # the form check reads "a) ..." as an answer option


def _line(text: str) -> str:
    return " ".join(text.split())


def _text(questions: list[_Question]) -> str:
    """The questions as the form check reads them. The board's own required flag replaces any mark in the label."""
    lines = []
    for question in questions:
        label = _MARKS.sub("", _BULLET.sub("", _line(question.label)))
        if not label:
            continue
        if _LETTERED.match(label):
            label = label[0].upper() + label[1:]
        mark = {True: " *", False: " (optional)", None: ""}[question.required]
        options = [option for option in dict.fromkeys(map(_line, question.options)) if option and option != label]
        lines += [label + mark, *(f"- {option}" for option in options[:MAX_OPTIONS])]
        if len(options) > MAX_OPTIONS:
            lines.append(f"- … and {len(options) - MAX_OPTIONS} more")
    return "\n".join(lines)


def _flag(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _dicts(items: object) -> list[dict[str, Any]]:
    return [cast(dict[str, Any], item) for item in items if isinstance(item, dict)] if isinstance(items, list) else []


# Greenhouse: https://developers.greenhouse.io/job-board.html#retrieve-a-job. Location, the EEOC and demographic
# questions and the education section come in their own lists, which aren't read.

_GREENHOUSE_STANDARD = {
    "first_name", "last_name", "preferred_name", "email", "phone", "resume", "resume_text", "cover_letter",
    "cover_letter_text",
}  # fmt: skip


def _greenhouse(token: str, posting: str, fetcher: Fetcher) -> str | None:
    job = fetcher.json(f"https://boards-api.greenhouse.io/v1/boards/{quote(token, safe='')}/jobs/"
                       f"{quote(posting, safe='')}?questions=true")  # fmt: skip
    if not isinstance(job, dict):
        raise FetchError("The job board sent something we couldn't read. Try again later.")
    if not isinstance(job.get("questions"), list):
        return None
    questions = []
    for question in _dicts(job["questions"]):
        fields = [item for item in _dicts(question.get("fields")) if item.get("type") != "input_hidden"]
        if not fields or all(item.get("name") in _GREENHOUSE_STANDARD for item in fields):
            continue  # the board's own fields, or one the applicant never sees
        options = [str(value.get("label") or "") for item in fields for value in _dicts(item.get("values"))]
        questions.append(_Question(str(question.get("label") or ""), _flag(question.get("required")), options))
    return _text(questions)


# Lever: the apply page, https://jobs.lever.co/{site}/{posting}/apply. The demographic survey's cards
# (surveysResponses[...]) and the board's own fields aren't read.

_LEVER_CARD = re.compile(r"cards\[[^\]]+\]\[baseTemplate\]")


class _LeverForm(HTMLParser):
    """The apply page's form: each card's JSON template, and how many of the employer's questions the page shows."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found = False
        self.cards: list[object] = []
        self.shown = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attrs}
        if tag == "form" and values.get("id") == "application-form":
            self.found = True
        elif tag == "input" and _LEVER_CARD.fullmatch(values.get("name", "")):
            try:
                self.cards.append(json.loads(values.get("value", "")))
            except ValueError:
                self.cards.append(None)
        elif tag == "li" and "custom-question" in values.get("class", "").split():
            self.shown += 1


def _lever(site: str, posting: str, fetcher: Fetcher) -> str | None:
    markup, _ = fetcher.text(f"https://jobs.lever.co/{quote(site, safe='')}/{quote(posting, safe='')}/apply",
                             MAX_PAGE_BYTES)  # fmt: skip
    page = _LeverForm()
    page.feed(markup)
    page.close()
    if not page.found:
        return None  # no application form on the page
    questions = [
        _Question(str(item.get("text") or ""), _flag(item.get("required")),
                  [str(option.get("text") or "") for option in _dicts(item.get("options"))])
        for card in page.cards if isinstance(card, dict) for item in _dicts(card.get("fields"))
    ]  # fmt: skip
    if page.shown > len(questions):
        return None  # questions on the page that its cards don't carry: this form isn't read in full
    return _text(questions)
