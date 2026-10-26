"""Reading a posting's application form from its job board, as the text the form check reads.

greenhouse_questions.json and lever_apply.html are real responses (2026-10-26): Faire's Toronto posting with
?questions=true (its posting text replaced by greenhouse_job.json's made-up one, its demographic survey cut short),
and the apply page of Achievers' posting cut to its form, with the Lever account and user ids zeroed.
"""

import json
from typing import Any

import pytest

from app.audit.boards import Source
from app.audit.fetch import FetchError, RobotsRefused, Unavailable
from app.audit.forms import MAX_OPTIONS, application_form
from app.compliance.form import parse_form
from tests.audit.web import Web, boards

GREENHOUSE = "boards-api.greenhouse.io/v1/boards/faire/jobs"
LEVER = "jobs.lever.co/achievers/cfd24914-023d-4cc7-a8a1-433582958dbe"


def forms() -> Web:
    web = boards()
    web.file(f"{GREENHOUSE}/8821336002?questions=true", "greenhouse_questions.json")
    web.page("jobs.lever.co/robots.txt", "User-agent: *\nAllow: /\nCrawl-delay: 1\n")  # as on 2026-10-26
    web.file(f"{LEVER}/apply", "lever_apply.html")
    return web


def test_greenhouse() -> None:
    form = application_form("greenhouse", "faire", "8821336002", forms().fetcher())
    assert form is not None
    questions = parse_form(form).questions
    assert [(q.text[:45], q.required, len(q.options)) for q in questions] == [
        ("LinkedIn Profile", False, 0),
        ("Website", False, 0),
        ("Please select your current province of reside", True, 14),
        ("This role will be in-office on a hybrid sched", True, 2),
        ("Before seeing this job posting, how familiar ", True, 4),
        ("How did you hear about Faire? (Select all tha", True, 11),
    ]  # fmt: skip
    assert form.startswith("LinkedIn Profile (optional)\nWebsite (optional)\nPlease select your current province")
    assert "\n- Ontario\n" in form
    # the board's own fields, the location question and the voluntary demographic survey are left out
    for left_out in ("First Name", "Email", "Phone", "Resume", "Cover Letter", "Location", "gender", "categories"):
        assert left_out not in form


def test_lever() -> None:
    web = forms()
    form = application_form("lever", "achievers", "cfd24914-023d-4cc7-a8a1-433582958dbe", web.fetcher())
    assert form == (
        "Are you legally entitled to work in the country you are applying for? *\n- Yes\n- No\n"
        "Do you now or will you in the future require sponsorship from an employer to work in the country for which "
        "you are applying? *\n- Yes\n- No\n"
        "Are you willing to go through a background check (which includes: employment, education, and criminal "
        "verification) at the time an offer is extended? *\n- Yes\n- No\n"
        "How did you hear about this opportunity? *\n- Glassdoor\n- Achievers Career Page\n- LinkedIn\n- Indeed\n"
        "- Networking Event\n- Other\n"
        "Are you comfortable working in a hybrid work arrangement 2-3 days a week, which involves a combination of "
        "remote work and in-office collaboration? (for roles posted as hybrid only) *\n- Yes\n- No\n"
        "Please provide your salary range requirements: *"
    )  # the résumé, contact and link fields and the demographic survey are left out
    assert len(parse_form(form).questions) == 6
    assert web.asked()[-1] == f"{LEVER}/apply"


def _lever_page(*cards: dict[str, Any], shown: int | None = None) -> str:
    """An apply page with these cards of questions, each shown as a custom question unless `shown` says otherwise."""
    fields = sum(len(card["fields"]) for card in cards)
    inputs = "".join(
        f'<input type="hidden" value="{json.dumps(card).replace(chr(34), "&quot;")}" name="cards[c{n}][baseTemplate]">'
        for n, card in enumerate(cards)
    )  # fmt: skip
    questions = '<li class="application-question custom-question">…</li>' * (fields if shown is None else shown)
    return f'<form id="application-form">{inputs}<ul>{questions}</ul></form>'


def test_the_boards_required_flag_marks_each_question() -> None:
    countries = [f"Country {n}" for n in range(MAX_OPTIONS + 5)]
    card = {"text": "Screening", "fields": [
        {"type": "text", "text": "Canadian work experience (years) *", "required": False},
        {"type": "textarea", "text": "  Why\n  this   role?  (optional)", "required": True},
        {"type": "multiple-choice", "text": "a) Where did you study?", "required": True,
         "options": [{"text": "In Canada"}, {"text": "Elsewhere"}, {"text": "In Canada"}]},
        {"type": "dropdown", "text": "• Where have you worked?", "options": [{"text": c} for c in countries]},
        {"type": "text", "text": " ", "required": True},
    ]}  # fmt: skip
    web = forms().page("jobs.lever.co/northwind/1/apply", _lever_page(card, shown=5))
    form = application_form("lever", "northwind", "1", web.fetcher())
    assert form == "\n".join([
        "Canadian work experience (years) (optional)", "Why this role? *", "A) Where did you study? *", "- In Canada",
        "- Elsewhere", "Where have you worked?", *(f"- Country {n}" for n in range(MAX_OPTIONS)), "- … and 5 more",
    ])  # fmt: skip
    questions = parse_form(form).questions
    assert [(q.text, q.required, len(q.options)) for q in questions] == [
        ("Canadian work experience (years)", False, 0), ("Why this role?", True, 0),
        ("A) Where did you study?", True, 2), ("Where have you worked?", None, MAX_OPTIONS + 1),
    ]  # fmt: skip


def test_a_lever_form_with_only_the_boards_own_fields_is_empty() -> None:
    web = forms().page("jobs.lever.co/northwind/1/apply", _lever_page())
    assert application_form("lever", "northwind", "1", web.fetcher()) == ""


def test_a_lever_form_we_cant_read_in_full() -> None:
    web = forms()
    web.page("jobs.lever.co/northwind/1/apply", "<h2>Apply on our website</h2>")  # no form on the page
    web.page("jobs.lever.co/northwind/2/apply", _lever_page(shown=2))  # questions shown without their cards
    assert application_form("lever", "northwind", "1", web.fetcher()) is None
    assert application_form("lever", "northwind", "2", web.fetcher()) is None


def test_a_greenhouse_answer_without_questions() -> None:
    web = forms()
    web.page(f"{GREENHOUSE}/1?questions=true", json.dumps({"id": 1, "title": "Buyer"}))
    web.page(f"{GREENHOUSE}/2?questions=true", json.dumps({"id": 2, "questions": [
        {"label": "Email", "required": True, "fields": [{"name": "email", "type": "input_text"}]},
        {"label": "Source", "required": False, "fields": [{"name": "question_9", "type": "input_hidden"}]},
    ]}))  # fmt: skip
    web.page(f"{GREENHOUSE}/3?questions=true", "[]")
    fetcher = web.fetcher()
    assert application_form("greenhouse", "faire", "1", fetcher) is None
    assert application_form("greenhouse", "faire", "2", fetcher) == ""
    with pytest.raises(FetchError, match="couldn't read"):
        application_form("greenhouse", "faire", "3", fetcher)


@pytest.mark.parametrize("source", ["ashby", "smartrecruiters", "page"])
def test_boards_whose_forms_arent_read(source: Source) -> None:
    web = forms()
    assert application_form(source, "cohere", "7133d205-5421-4336-a8e2-6037b5f55073", web.fetcher()) is None
    assert web.requests == []


def test_fetch_failures_raise() -> None:
    web = forms()
    with pytest.raises(Unavailable):  # the posting is gone
        application_form("greenhouse", "faire", "1", web.fetcher())
    web.page("jobs.lever.co/robots.txt", "User-agent: *\nDisallow: /\n")
    with pytest.raises(RobotsRefused, match="jobs.lever.co"):
        application_form("lever", "achievers", "cfd24914-023d-4cc7-a8a1-433582958dbe", web.fetcher())
