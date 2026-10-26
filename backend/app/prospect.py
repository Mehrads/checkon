"""A company's public job board, checked for the outreach workflow (.claude/workflows/prospect-outreach.js): its
first postings for Ontario, picked as the free sample audit picks them, each with its findings, the posting's own
words for each and the rule page to link, so a pitch can quote them. Nothing is saved to the database; the checks
use the real model on ANTHROPIC_API_KEY.

    python -m app.prospect https://job-boards.greenhouse.io/acme --postings 3 --out ../prospecting/2026-10-26/acme

Prints JSON. With --out, each checked posting's text is saved there too (posting-1.txt, ...), so the findings can be
checked against what was read.
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import anthropic

from app.api.routes.audits import MAX_POSTING_CHARS
from app.audit.boards import Board, Found, posting_text, read_board
from app.audit.fetch import Fetcher, FetchError
from app.compliance.employer import EmployerSize, SizeCache
from app.compliance.inspector import InputRefused, inspect
from app.compliance.llm import AnthropicLLM, LLMError, SpendMeter, StructuredLLM
from app.compliance.models import Context, Verdict
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
    to_act = sorted((r for r in report.results if r.verdict in _ORDER), key=lambda r: _ORDER[r.verdict])
    return out | {
        "status": report.status.value,
        "passed": sum(r.verdict == Verdict.PASS for r in report.results),
        "findings": [
            {
                "rule": r.rule, "verdict": r.verdict.value, "message": r.message, "page": page_for(r.rule),
                "quotes": [doc.text[start:end] for start, end in r.evidence],
            }
            for r in to_act
        ],
        "employer_size": {
            "meets_threshold": ctx.meets_headcount_threshold, "basis": ctx.headcount_basis,
            "evidence": ctx.headcount_evidence,
        },
    }  # fmt: skip


def prospect(
    url: str, fetcher: Fetcher, llm: StructuredLLM, pack: RulePack, today: date, sizes: SizeCache, postings: int = 3
) -> dict[str, Any]:
    """The board and its first Ontario postings, checked. Raises FetchError when the board can't be read."""
    board = read_board(url, fetcher, today)
    picked = first_postings(board, postings)
    in_ontario = sum(p.where in ("ontario", "canada") for p in board.postings)
    return {
        "board": {"source": board.source, "key": board.key, "name": board.name, "url": board.url},
        "in_ontario": in_ontario,
        "outside_ontario": len(board.postings) - in_ontario,
        "postings": [check_posting(board, found, fetcher, llm, pack, today, sizes) for found in picked],
    }


def save_texts(result: dict[str, Any], out: Path) -> dict[str, Any]:
    """Each checked posting's text to out/posting-N.txt; the JSON then names the file instead of carrying the text."""
    out.mkdir(parents=True, exist_ok=True)
    for n, posting in enumerate(result.get("postings", []), start=1):
        if (text := posting.pop("text", None)) is not None:
            (out / f"posting-{n}.txt").write_text(text, encoding="utf-8")
            posting["text_file"] = str(out / f"posting-{n}.txt")
    (out / "check.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("url", help="the company's job board or careers page")
    parser.add_argument("--postings", type=int, default=settings.SAMPLE_AUDIT_POSTINGS, help="how many to check")
    parser.add_argument("--out", type=Path, help="a folder for the posting texts and check.json")
    args = parser.parse_args()
    if not settings.ANTHROPIC_API_KEY:
        raise SystemExit("ANTHROPIC_API_KEY is not set: the checks need the model.")
    meter = SpendMeter()
    llm = AnthropicLLM(anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY), meter=meter)
    fetcher = Fetcher()
    try:
        result = prospect(
            args.url, fetcher, llm, load_pack("CA-ON"), datetime.now(TORONTO).date(), MemorySizes(),
            args.postings,
        )  # fmt: skip
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
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
