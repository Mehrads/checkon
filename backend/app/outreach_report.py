"""Save an outreach check on checkon.ca as the report the pitch email links to (app/api/routes/reports.py). The outreach
workflow runs it after a second agent has confirmed the findings: it reads the check's JSON (app.prospect's output,
with the findings that weren't confirmed taken out) and prints the report's private link.

    python -m app.outreach_report ~/Documents/CheckON/prospecting/2026-10-26/acme/confirmed.json --company "Acme"

Needs OUTREACH_API_KEY (the same value as the site's). --site points it at a local server for testing. Only what
the report shows is sent: titles, places, links, findings with short quotes. No posting text, no contacts.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings

MAX_QUOTES = 5  # per finding, as the API takes them
MAX_QUOTE_CHARS = 300


def _findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"rule": f["rule"], "verdict": f["verdict"], "message": f["message"][:500],
         "quotes": [q[:MAX_QUOTE_CHARS] for q in f.get("quotes", [])[:MAX_QUOTES]]}
        for f in findings
    ]  # fmt: skip


def report_body(check: dict[str, Any], company: str) -> dict[str, Any]:
    """The API's report from app.prospect's JSON: the fields the report shows, and nothing else."""
    postings = []
    for posting in check.get("postings", []):
        postings.append({
            "title": posting["title"][:255], "location": (posting.get("location") or None),
            "url": posting["url"], "where": posting["where"], "status": posting["status"],
            "note": (posting.get("note") or posting.get("form_note") or None),
            "findings": _findings(posting.get("findings", [])),
            "form_status": posting.get("form_status"), "form_findings": _findings(posting.get("form_findings", [])),
        })  # fmt: skip
    return {
        "company": company, "url": check["board"]["url"],
        "found": check.get("in_ontario", 0) + check.get("outside_ontario", 0),
        "outside_ontario": check.get("outside_ontario", 0), "postings": postings,
    }  # fmt: skip


def save_report(body: dict[str, Any], site: str, key: str, client: httpx.Client) -> dict[str, Any]:
    response = client.post(
        f"{site.rstrip('/')}{settings.API_V1_STR}/outreach/reports", json=body,
        headers={"Authorization": f"Bearer {key}"}, timeout=30,
    )  # fmt: skip
    response.raise_for_status()
    return dict(response.json())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("check", type=Path, help="app.prospect's JSON, with unconfirmed findings taken out")
    parser.add_argument("--company", required=True, help="the company's name, as the report's title shows it")
    parser.add_argument("--site", default="https://checkon.ca", help="the site to save it on")
    args = parser.parse_args()
    if not settings.OUTREACH_API_KEY:
        raise SystemExit("OUTREACH_API_KEY is not set: the site won't take the report without it.")
    check = json.loads(args.check.expanduser().read_text())
    if "error" in check:
        raise SystemExit(f"That check has no report: {check['error']}")
    with httpx.Client() as client:
        try:
            saved = save_report(report_body(check, args.company), args.site, settings.OUTREACH_API_KEY, client)
        except httpx.HTTPStatusError as error:
            raise SystemExit(f"The site refused the report ({error.response.status_code}): {error.response.text[:500]}")
    json.dump(saved, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
