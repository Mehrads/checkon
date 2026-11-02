"""A company's public job board, checked for the outreach workflow (.claude/workflows/prospect-outreach.js): its
open postings for Ontario (all of them, up to --postings), picked as the free sample audit picks them, each with its
findings, the posting's own words for each and the rule page to link, so a pitch can quote them, and its application
form's findings where the board shows the form (Greenhouse, Lever). Nothing is saved to the database; the checks use
the real model on ANTHROPIC_API_KEY. Once a second agent has confirmed the findings, `python -m app.outreach_report`
saves them on checkon.ca as the report the email links to.

    python -m app.prospect https://job-boards.greenhouse.io/acme --out ~/Documents/CheckON/prospecting/2026-10-26/acme

An employer with no job board to read, such as a town that posts each job as a web page or a PDF, is checked one
posting at a time. PDFs need poppler's pdftotext (brew install poppler):

    python -m app.prospect https://town.example/jobs --page https://town.example/jobs/clerk "Records Clerk" --out ...

Prints JSON. With --out, each checked posting's text and form are saved there too (posting-1.txt, form-1.txt, ...),
so the findings can be checked against what was read.
"""

import argparse
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import anthropic

from app.api.routes.audits import MAX_POSTING_CHARS, MAX_POSTINGS
from app.audit.boards import MAX_PAGE_BYTES, Board, Found, posting_text, read_board
from app.audit.fetch import Fetcher, FetchError
from app.audit.forms import application_form
from app.compliance import webpage
from app.compliance.employer import EmployerSize, SizeCache
from app.compliance.engine import evaluate
from app.compliance.form import classify_form, parse_form
from app.compliance.inspector import InputRefused, Inspection, inspect
from app.compliance.llm import (
    AnthropicLLM,
    LLMError,
    ModelSettings,
    SpendMeter,
    StructuredLLM,
)
from app.compliance.models import Context, RuleResult, Status, Verdict
from app.compliance.rulepack import RulePack, load_pack
from app.core.config import settings

TORONTO = ZoneInfo("America/Toronto")
_ORDER = {Verdict.FAIL: 0, Verdict.WARNING: 1, Verdict.NEEDS_INPUT: 2}
_UTM = "?utm_source=email&utm_medium=outreach&utm_campaign=careers-audit"
# The public page that explains each rule, with wording to copy
RULE_PAGES = {
    "ON-PAY-01": "/ontario-pay-transparency-job-posting",
    "ON-PAY-02": "/ontario-pay-transparency-job-posting",
    "ON-CEX-01": "/ontario-canadian-experience-job-posting",
    "ON-AI-01": "/ontario-ai-disclosure-job-posting",
    "ON-VAC-01": "/ontario-existing-vacancy-job-posting",
}


class MemorySizes(dict[tuple[str, str], EmployerSize]):
    """Employer-size searches for this run only: the command doesn't need the database."""

    def put(self, key: tuple[str, str], value: EmployerSize) -> None:
        self[key] = value


def page_for(rule: str) -> str:
    return f"https://checkon.ca{RULE_PAGES.get(rule, '/ontario-job-posting-requirements')}{_UTM}"


def _findings(results: list[RuleResult], text: str) -> list[dict[str, Any]]:
    """What to act on, worst first, with the words each points at in `text`."""
    to_act = sorted((r for r in results if r.verdict in _ORDER), key=lambda r: _ORDER[r.verdict])
    return [
        {"rule": r.rule, "verdict": r.verdict.value, "message": r.message, "page": page_for(r.rule),
         "quotes": [text[start:end] for start, end in r.evidence]}
        for r in to_act
    ]  # fmt: skip


def check_form(
    board: Board, found: Found, inspection: Inspection, fetcher: Fetcher, llm: StructuredLLM, pack: RulePack,
    today: date,
) -> dict[str, Any]:  # fmt: skip
    """The posting's application form, read from the board and checked as the form check does; form_status None
    when the board doesn't show it or it couldn't be read or checked."""
    try:
        text = application_form(board.source, board.key, found.id, fetcher)
    except FetchError as error:
        return {"form_status": None, "form_note": f"The application form couldn't be read: {str(error)[:200]}"}
    if text is None:
        return {"form_status": None}
    form = parse_form(text)
    if not form.questions:  # only the board's own fields (name, email, résumé): nothing asks about experience
        return {"form_status": Status.COMPLIANT.value, "form_findings": [], "form_text": text}
    try:
        questions = classify_form(form, pack, llm, ModelSettings())
    except LLMError:
        return {"form_status": None, "form_note": "The model couldn't check the application form."}
    facts = inspection.facts.model_copy(update={"form": questions})
    report = evaluate(facts, inspection.context, pack, today)
    failed = any(r.verdict == Verdict.FAIL for r in report.form_results)
    return {
        "form_status": (Status.NOT_COMPLIANT if failed else Status.COMPLIANT).value,
        "form_findings": _findings(report.form_results, form.text), "form_text": text,
    }  # fmt: skip


def first_postings(board: Board, count: int) -> list[Found]:
    """Ontario's postings first, then Canada-wide ones that may be filled in Ontario, as the sample audit picks."""
    ontario = [p for p in board.postings if p.where == "ontario"] + [p for p in board.postings if p.where == "canada"]
    return ontario[:count]


def check_posting(
    board: Board, found: Found, fetcher: Fetcher, llm: StructuredLLM, pack: RulePack, today: date, sizes: SizeCache
) -> dict[str, Any]:
    """One posting's findings, worst first, with the words each points at; or why it wasn't checked."""
    out: dict[str, Any] = {"title": found.title, "location": found.location, "url": found.url, "where": found.where}
    try:
        text = found.text or posting_text(board.source, board.key, found.id, found.url, fetcher, today)
    except FetchError as error:
        return out | {"status": "failed", "note": str(error)[:255]}
    out["text"] = text
    if len(text) > MAX_POSTING_CHARS:
        return out | {"status": "refused", "note": f"Over {MAX_POSTING_CHARS:,} characters: too long to check."}
    try:
        inspection = inspect(text, Context(), today, pack, llm, sizes=sizes)
    except InputRefused as error:
        return out | {"status": "refused", "note": error.message}
    except LLMError:
        return out | {"status": "failed", "note": "The model couldn't check this posting."}
    report, doc, ctx = inspection.report, inspection.document, inspection.context
    out |= {
        "status": report.status.value,
        "passed": sum(r.verdict == Verdict.PASS for r in report.results),
        "findings": _findings(report.results, doc.text),
        "employer_size": {
            "meets_threshold": ctx.meets_headcount_threshold, "basis": ctx.headcount_basis,
            "evidence": ctx.headcount_evidence,
        },
    }  # fmt: skip
    if report.status != Status.NOT_APPLICABLE:  # the rules cover the form only where they cover the posting
        out |= check_form(board, found, inspection, fetcher, llm, pack, today)
    return out


def pdf_text(data: bytes) -> str:
    """A PDF's text, empty when it has none (a scan) or poppler can't read it."""
    done = subprocess.run(["pdftotext", "-", "-"], input=data, capture_output=True, timeout=30)
    return done.stdout.decode("utf-8", errors="replace").strip() if done.returncode == 0 else ""


def page_text(url: str, fetcher: Fetcher) -> str:
    """The posting at `url`, a web page or a PDF; empty when there's little text."""
    body, _ = fetcher.content(url, MAX_PAGE_BYTES)
    if not body.startswith(b"%PDF"):
        return webpage.posting_text(body.decode("utf-8", errors="replace"))
    text = pdf_text(body)
    return text if len(text) >= webpage.MIN_POSTING_CHARS else ""


def read_pages(careers: str, pages: list[tuple[str, str]], fetcher: Fetcher) -> Board:
    """Each (address, title) as one posting, for an employer whose careers page has no job board to read. The outreach
    workflow has already confirmed the jobs are in Ontario. A page that can't be read stays in the list with no text,
    and check_posting says why."""
    postings = []
    for url, title in pages:
        try:
            text = page_text(url, fetcher)
        except FetchError:
            text = ""
        postings.append(Found(id=url, title=title, location="Ontario", url=url, where="ontario", text=text or None))
    return Board("page", careers, None, careers, postings)


def prospect(
    url: str, fetcher: Fetcher, llm: StructuredLLM, pack: RulePack, today: date, sizes: SizeCache,
    postings: int = MAX_POSTINGS,
) -> dict[str, Any]:  # fmt: skip
    """The board and its Ontario postings, up to `postings`, checked. Raises FetchError when the board can't be read."""
    return check_board(read_board(url, fetcher, today), fetcher, llm, pack, today, sizes, postings)


def check_board(
    board: Board, fetcher: Fetcher, llm: StructuredLLM, pack: RulePack, today: date, sizes: SizeCache, postings: int
) -> dict[str, Any]:
    picked = first_postings(board, postings)
    in_ontario = sum(p.where in ("ontario", "canada") for p in board.postings)
    return {
        "board": {"source": board.source, "key": board.key, "name": board.name, "url": board.url},
        "in_ontario": in_ontario,
        "outside_ontario": len(board.postings) - in_ontario,
        "postings": [check_posting(board, found, fetcher, llm, pack, today, sizes) for found in picked],
    }


def save_texts(result: dict[str, Any], out: Path) -> dict[str, Any]:
    """Each checked posting's text to out/posting-N.txt and its form to out/form-N.txt; the JSON then names the files
    instead of carrying the text."""
    out.mkdir(parents=True, exist_ok=True)
    for n, posting in enumerate(result.get("postings", []), start=1):
        if (text := posting.pop("text", None)) is not None:
            (out / f"posting-{n}.txt").write_text(text, encoding="utf-8")
            posting["text_file"] = str(out / f"posting-{n}.txt")
        if form := posting.pop("form_text", None):
            (out / f"form-{n}.txt").write_text(form, encoding="utf-8")
            posting["form_file"] = str(out / f"form-{n}.txt")
    (out / "check.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("url", help="the company's job board or careers page")
    parser.add_argument("--page", nargs=2, action="append", metavar=("URL", "TITLE"),
                        help="check this posting's own web page or PDF instead of reading the board; repeat for each")  # fmt: skip
    parser.add_argument("--postings", type=int, default=MAX_POSTINGS, help="at most this many to check")
    parser.add_argument("--out", type=Path, help="a folder for the posting texts and check.json")
    args = parser.parse_args()
    if not settings.ANTHROPIC_API_KEY:
        raise SystemExit("ANTHROPIC_API_KEY is not set: the checks need the model.")
    meter = SpendMeter()
    llm = AnthropicLLM(anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY), meter=meter)
    fetcher = Fetcher()
    today = datetime.now(TORONTO).date()
    try:
        if args.page:
            board = read_pages(args.url, [(url, title) for url, title in args.page], fetcher)
            result = check_board(board, fetcher, llm, load_pack("CA-ON"), today, MemorySizes(), args.postings)
        else:
            result = prospect(args.url, fetcher, llm, load_pack("CA-ON"), today, MemorySizes(), args.postings)
    except FetchError as error:
        result = {"error": str(error)[:500]}
    finally:
        fetcher.client.close()
    result["usd"] = str(meter.usd)
    if args.out:
        result = save_texts(result, args.out)
    else:
        for posting in result.get("postings", []):
            posting.pop("text", None)
            posting.pop("form_text", None)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
