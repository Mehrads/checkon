"""The outreach workflow's check of a company's board (app/prospect.py), with a recorded web and a scripted LLM (no
network): the first Ontario postings, each finding with the posting's own words and the rule page to link."""

import json
from datetime import date
from pathlib import Path

import pytest

from app.audit.fetch import FetchError
from app.compliance.classification import Classification
from app.compliance.extraction import Extraction
from app.compliance.rulepack import load_pack
from app.prospect import MemorySizes, page_for, prospect, save_texts
from tests.api.routes.test_audits import CAREERS, northwind
from tests.compliance.fake_llm import FakeLLM
from tests.compliance.test_inspector import extraction, labels

TODAY = date(2026, 10, 23)


def test_the_first_ontario_postings_with_quotes_and_pages() -> None:
    llm = FakeLLM()
    for _ in range(2):
        llm.queue(Extraction, extraction()).queue(Classification, labels())
    result = prospect(CAREERS, northwind().fetcher(), llm, load_pack("CA-ON"), TODAY, MemorySizes(), postings=2)

    assert (result["board"]["source"], result["in_ontario"], result["outside_ontario"]) == ("page", 3, 1)
    assert [(p["title"], p["where"], p["status"]) for p in result["postings"]] == [
        ("Payroll Specialist", "ontario", "not_compliant"), ("Payroll Specialist", "ontario", "not_compliant"),
    ]  # two asked for, Calgary never in the running
    first = result["postings"][0]
    cex = next(f for f in first["findings"] if f["rule"] == "ON-CEX-01")
    assert cex["verdict"] == "fail" and cex["message"]
    assert any("Canadian payroll experience" in quote for quote in cex["quotes"])  # the posting's own words
    assert cex["page"] == page_for("ON-CEX-01")
    assert cex["page"].startswith("https://checkon.ca/ontario-canadian-experience-job-posting?utm_source=email")
    assert [f["verdict"] for f in first["findings"]] == sorted(
        (f["verdict"] for f in first["findings"]), key=["fail", "warning", "needs_input"].index
    )  # worst first
    assert "Canadian payroll experience" in first["text"]


def test_saving_the_texts_for_review(tmp_path: Path) -> None:
    llm = FakeLLM().queue(Extraction, extraction()).queue(Classification, labels())
    result = prospect(CAREERS, northwind().fetcher(), llm, load_pack("CA-ON"), TODAY, MemorySizes(), postings=1)
    saved = save_texts(result, tmp_path / "northwind")

    posting = saved["postings"][0]
    assert "text" not in posting and Path(posting["text_file"]).read_text().startswith("Payroll Specialist")
    assert json.loads((tmp_path / "northwind" / "check.json").read_text()) == saved


def test_a_board_that_cant_be_read() -> None:
    with pytest.raises(FetchError):
        prospect("https://northwind.example/nothing-here", northwind().fetcher(), FakeLLM(), load_pack("CA-ON"),
                 TODAY, MemorySizes())  # fmt: skip
