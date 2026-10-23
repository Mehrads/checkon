"""The posting text of a fetched page: JSON-LD JobPosting first, else the page's main content."""

import json
from typing import Any

from app.compliance.webpage import html_to_text, posting_text

DESCRIPTION = (
    "<p>We're growing. You'll run payroll for 400 employees across our Ontario sites.</p>"
    "<h3>Requirements</h3><ul><li>2+ years of payroll experience</li><li>CPP certification is an asset</li></ul>"
    "<p>This posting is for an existing vacancy. We do not use AI to screen applicants.</p>"
)


def json_ld(data: Any, page: str = "<div id='root'></div>") -> str:
    return f'<html><head><script type="application/ld+json">{json.dumps(data)}</script></head><body>{page}</body></html>'


def job(**changes: Any) -> dict[str, Any]:
    return {
        "@context": "https://schema.org", "@type": "JobPosting", "title": "Payroll Specialist",
        "hiringOrganization": {"@type": "Organization", "name": "Northwind Logistics"},
        "jobLocation": {"@type": "Place", "address": {"addressLocality": "Mississauga", "addressRegion": "ON"}},
        "description": DESCRIPTION, **changes,
    }  # fmt: skip


def test_json_ld_job_posting_is_read_with_its_title_employer_and_place() -> None:
    text = posting_text(json_ld(job()))
    assert text.startswith("Payroll Specialist\n\nNorthwind Logistics · Mississauga, ON\n\nWe're growing.")
    assert "Requirements\n• 2+ years of payroll experience\n• CPP certification is an asset" in text


def test_pay_from_the_structured_data_is_added_when_the_description_has_none() -> None:
    salary = {"@type": "MonetaryAmount", "currency": "CAD",
              "value": {"@type": "QuantitativeValue", "minValue": 60000, "maxValue": 80000, "unitText": "YEAR"}}  # fmt: skip
    assert posting_text(json_ld(job(baseSalary=salary))).endswith("Pay: $60,000 to $80,000 a year.")
    hourly = {"currency": "CAD", "value": {"value": 27.5, "unitText": "HOUR"}}
    assert posting_text(json_ld(job(baseSalary=hourly))).endswith("Pay: $27.50 an hour.")


def test_pay_already_in_the_description_is_not_added_twice() -> None:
    salary = {"currency": "CAD", "value": {"minValue": 60000, "maxValue": 80000, "unitText": "YEAR"}}
    described = job(description=DESCRIPTION + "<p>Salary: $60,000 – $80,000 per year.</p>", baseSalary=salary)
    text = posting_text(json_ld(described))
    assert "Pay:" not in text and "Salary: $60,000 – $80,000 per year." in text


def test_a_job_posting_inside_a_graph_or_with_several_types_is_found() -> None:
    graph = {"@context": "https://schema.org", "@graph": [{"@type": "WebPage"}, job(**{"@type": ["JobPosting", "Thing"]})]}
    assert posting_text(json_ld(graph)).startswith("Payroll Specialist")
    assert posting_text(json_ld([{"@type": "Organization"}, job()])).startswith("Payroll Specialist")


def test_a_description_escaped_twice_is_read_as_html() -> None:
    escaped = DESCRIPTION.replace("<", "&lt;").replace(">", "&gt;")
    assert "• 2+ years of payroll experience" in posting_text(json_ld(job(description=escaped)))


def test_without_json_ld_the_main_content_is_read_and_page_chrome_left_out() -> None:
    page = f"""<html><body><header>Logo · Jobs</header><nav>Home</nav>
    <main><h1>Payroll Specialist</h1>{DESCRIPTION}<script>track()</script>
    <form><label>Email</label><input name=email><select><option>Toronto</option></select></form></main>
    <aside>Similar jobs</aside><footer>Privacy</footer></body></html>"""
    text = posting_text(page)
    assert text.startswith("Payroll Specialist\nWe're growing.")
    for chrome in ("Logo", "Home", "track()", "Similar jobs", "Privacy", "Toronto"):
        assert chrome not in text


def test_an_application_form_under_the_posting_is_left_out() -> None:
    """Greenhouse and Lever pages put the application form inside the main content, under the posting."""
    page = f"""<html><body><main><h1>Payroll Specialist</h1>{DESCRIPTION}
    <form id="application-form"><h2>Apply for this job</h2><label>First name*</label><input>
    <label>Do you have Canadian work experience?</label><div>Select...</div></form></main></body></html>"""
    text = posting_text(page)
    assert "• CPP certification is an asset" in text
    assert "Apply for this job" not in text and "First name" not in text and "Select..." not in text


def test_a_page_wrapped_in_one_form_is_still_read() -> None:
    page = f"<html><body><form id='aspnetForm'><div class='job'><h1>Payroll Specialist</h1>{DESCRIPTION}</div></form></body></html>"
    assert "• CPP certification is an asset" in posting_text(page)


def test_a_short_json_ld_description_falls_back_to_the_page() -> None:
    page = json_ld(job(description="<p>See below.</p>"), f"<article><h1>Payroll Specialist</h1>{DESCRIPTION}</article>")
    assert posting_text(page).startswith("Payroll Specialist\nWe're growing.")


def test_a_page_with_little_text_has_no_posting() -> None:
    assert posting_text("<html><body><div id='root'></div><script>app()</script></body></html>") == ""
    assert posting_text("<html><body><main><p>Jobs</p></main></body></html>") == ""


def test_html_to_text_keeps_list_items_and_headings_on_their_own_lines() -> None:
    assert html_to_text("<h2>Duties</h2><ul><li>Run payroll</li><li>File remittances</li></ul><p>Apply now.</p>") == (
        "Duties\n• Run payroll\n• File remittances\n\nApply now."
    )
    assert html_to_text("<p>Line one<br>Line two&nbsp;here</p>") == "Line one\n\nLine two here"
