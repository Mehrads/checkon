"""Add real postings to the golden set from a public job board (PRD §7: public ATS boards and careers pages,
respecting robots.txt; never LinkedIn or Indeed scraping).

    uv run python -m app.evals.collect https://boards.greenhouse.io/acme [--max 5]
    uv run python -m app.evals.collect https://jobs.lever.co/acme --outside-ontario --max 2

Reads the board with the careers page audit's reader (app/audit/boards.py: robots.txt, per-host pacing, size
limits). Keeps postings for work in Ontario (or, with --outside-ontario, the others, for the out-of-scope slice),
takes a few per employer so no one employer's template dominates, masks email addresses and phone numbers, and
writes each as an unlabelled case. A posting already in the set (same text) is skipped.

The postings stay in this private repository for testing; they aren't published.
"""

import argparse
import hashlib
import random
import re
import sys
from datetime import date
from pathlib import Path

from app.api.routes.checks import MAX_POSTING_CHARS
from app.audit.boards import Board, Found, posting_text, read_board
from app.audit.fetch import Fetcher, FetchError
from app.evals.cases import GOLDEN_DIR, Case, Source, load_cases, write_case

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE = re.compile(r"(?<![\d$])(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)")


def masked(text: str) -> str:
    """Email addresses and phone numbers out, so no recruiter's contact details sit in the repo. Names stay;
    the labeller removes a person's name if one appears."""
    return _PHONE.sub("[phone]", _EMAIL.sub("[email]", text))


def fingerprint(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).lower().encode()).hexdigest()[:16]


def case_id(board: Board, found: Found) -> str:
    raw = f"{board.source}-{board.key}-{found.id}".lower()
    return re.sub(r"[^a-z0-9]+", "-", raw).strip("-")[:80]


def picked(board: Board, outside: bool, most: int) -> list[Found]:
    wanted = [p for p in board.postings if (p.where != "ontario") == outside]
    return sorted(random.Random(board.key).sample(wanted, min(most, len(wanted))), key=lambda p: p.id)


def collect(url: str, *, outside: bool = False, most: int = 5, fetcher: Fetcher | None = None,
            today: date | None = None, root: Path = GOLDEN_DIR) -> list[Case]:  # fmt: skip
    fetcher = fetcher or Fetcher()
    today = today or date.today()
    board = read_board(url, fetcher, today)
    seen = {fingerprint(case.text) for case in load_cases(root)}
    added = []
    for found in picked(board, outside, most):
        text = found.text or posting_text(board.source, board.key, found.id, found.url, fetcher, today)
        text = masked(text)
        if fingerprint(text) in seen or len(text) > MAX_POSTING_CHARS:  # longer than the check accepts
            continue
        seen.add(fingerprint(text))
        case = Case(
            id=case_id(board, found), slice="out_of_scope" if outside else "real", posted=today, text=text,
            source=Source(url=found.url or board.url, board=board.source, employer=board.name,
                          location=found.location, fetched=today),
        )  # fmt: skip
        write_case(case, root)
        added.append(case)
    return added


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("url", help="the job board or careers page")
    parser.add_argument("--max", type=int, default=5, help="postings to take from this board (default 5)")
    parser.add_argument("--outside-ontario", action="store_true", help="take postings outside Ontario instead")
    args = parser.parse_args()
    try:
        cases = collect(args.url, outside=args.outside_ontario, most=args.max)
    except FetchError as error:
        sys.exit(f"{args.url}: {error}")
    for case in cases:
        print(f"{GOLDEN_DIR / case.slice / case.id}.yaml  {case.source.location if case.source else ''}")  # noqa: T201
    print(f"{len(cases)} added")  # noqa: T201


if __name__ == "__main__":
    main()
