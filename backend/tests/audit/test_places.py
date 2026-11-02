import pytest

from app.audit.places import vague, where


@pytest.mark.parametrize(("locations", "kwargs", "expected"), [
    (["Toronto, ON"], {}, "ontario"),
    (["Kitchener-Waterloo, ON; Toronto, ON"], {}, "ontario"),
    (["Mississauga, ON (hybrid)"], {}, "ontario"),
    (["Waterloo, Ontario"], {}, "ontario"),
    (["Toronto"], {}, "ontario"),
    (["Downtown Toronto"], {}, "ontario"),
    (["Greater Toronto Area"], {}, "ontario"),
    (["Toronto, Ont."], {}, "ontario"),
    (["Montreal, QC; Toronto, ON"], {}, "ontario"),
    (["Montreal, QC; Toronto"], {}, "ontario"),
    (["Toronto, Montreal, QC"], {}, "ontario"),
    (["Georgetown"], {}, "ontario"),  # in Halton Hills
    (["London"], {"country": "CA"}, "ontario"),  # London, Ontario
    (["Hamilton, Canada"], {}, "ontario"),
    (["Killarney, ON"], {"country": "CA"}, "ontario"),
    (["Killarney"], {"country": "CA"}, "ontario"),
    (["London, Ontario"], {}, "ontario"),
    (["Remote - Canada"], {}, "canada"),
    (["Killarney, MB"], {"country": "CA", "remote": True}, "canada"),
    (["Remote (US or Canada)"], {}, "canada"),
    (["Canada"], {"country": "CA", "remote": True}, "canada"),
    (["Remote"], {"country": "CA", "remote": True}, "canada"),
    ([], {"country": "CA"}, "canada"),
    (["London"], {"country": "GB"}, "elsewhere"),
    (["London, London, United Kingdom"], {}, "elsewhere"),
    (["Hamilton"], {}, "elsewhere"),  # also in New Zealand, Bermuda, Ohio…
    (["Ottawa, IL"], {}, "elsewhere"),
    (["Toronto, United States"], {}, "elsewhere"),
    (["Vancouver, BC"], {}, "elsewhere"),
    (["Vancouver, Canada"], {}, "elsewhere"),
    (["Halifax, Nova Scotia, Canada"], {}, "elsewhere"),
    (["Killarney, MB"], {"country": "CA"}, "elsewhere"),  # Lever's pharmachoicecanada
    (["Cochrane, AB"], {"country": "CA"}, "elsewhere"),
    (["Waterloo, Quebec, Canada"], {}, "elsewhere"),
    (["Georgetown, PE"], {}, "elsewhere"),
    (["Dundas (PE)"], {}, "elsewhere"),
    (["Dundas, Prince Edward Island, Canada"], {}, "elsewhere"),
    (["New York City, NY; San Francisco, CA"], {}, "elsewhere"),
    (["Remote - US"], {}, "elsewhere"),
    (["Remote"], {}, "elsewhere"),
    (["Sydney"], {"country": "AU", "remote": True}, "elsewhere"),
    # A town called Canada in a US state (bjrcrecruiting.com), against lists that name the country
    (["Canada, Nevada, US"], {}, "elsewhere"),
    (["Canada, Nevada, US"], {"country": "US"}, "elsewhere"),
    (["Canada, Nevada, United States"], {}, "elsewhere"),
    (["Canada, Nevada"], {}, "elsewhere"),
    (["Canada, NV, US"], {}, "elsewhere"),
    (["Canada, NV"], {}, "elsewhere"),
    (["Canada, CA, US"], {}, "elsewhere"),  # California
    (["Canada, CA"], {}, "canada"),  # the country, by name and by code
    (["Canada, US"], {}, "canada"),
    (["US, Canada"], {}, "canada"),
    (["Canada, USA"], {}, "canada"),
    (["Canada, Mexico, US"], {}, "canada"),
    (["Reno, Nevada, US", "Canada"], {}, "canada"),
    # The title names the place when the location says only Canada (Lever's pharmachoicecanada)
    (["Canada"], {"country": "CA", "title": "Pharmacist - FT or PT - Trail, BC"}, "elsewhere"),
    (["Canada"], {"country": "CA", "title": "Pharmacy Manager - Calgary AB"}, "elsewhere"),
    (["Canada"], {"country": "CA", "title": "Pharmacist - FT or PT - Cochrane, AB"}, "elsewhere"),
    (["Canada"], {"country": "CA", "title": "Pharmacist - Part Time - (Fluent in Cantonese) - Toronto, ON"}, "ontario"),
    (["Canada"], {"country": "CA", "title": "Pharmacist - Bilingual (French) an Asset - Sudbury, ON"}, "ontario"),
    (["Canada"], {"country": "CA", "title": "LTC Pharmacist - Simcoe, Ontario"}, "ontario"),
    (["Canada"], {"country": "CA", "title": "Pharmacist - FT or PT - Marathon, ON"}, "ontario"),
    (["Canada"], {"title": "Account Manager - Downtown Toronto"}, "ontario"),
    (["Canada"], {"title": "Sales Representative - Alberta"}, "elsewhere"),
    ([], {"country": "CA", "title": "Pharmacist - Trail, BC"}, "elsewhere"),
    (["Canada (on-site)"], {"title": "Pharmacist | Trail, BC"}, "elsewhere"),
    (["Canada"], {"country": "CA", "title": "Pharmacist"}, "canada"),
    (["Canada"], {"country": "CA", "title": "QC Analyst"}, "canada"),  # quality control
    (["Canada"], {"country": "CA", "title": "Lab Technician - QC"}, "canada"),
    (["Canada"], {"country": "CA", "remote": True, "title": "Pharmacist - Trail, BC"}, "canada"),  # open to anywhere
    (["Remote - Canada"], {"title": "Account Executive - Vancouver, BC"}, "canada"),
    (["US or Canada"], {"title": "Account Executive - Vancouver, BC"}, "canada"),
    (["Vancouver, BC"], {"title": "Engineer - Toronto, ON"}, "elsewhere"),  # the location comes first
    (["Toronto, ON"], {"title": "Engineer - Vancouver, BC"}, "ontario"),
])  # fmt: skip
def test_where(locations: list[str], kwargs: dict[str, object], expected: str) -> None:
    assert where(locations, **kwargs) == expected  # type: ignore[arg-type]


@pytest.mark.parametrize("province", [
    "AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "PE", "QC", "SK", "YT",
    "Alberta", "British Columbia", "Manitoba", "New Brunswick", "Newfoundland and Labrador", "Nova Scotia",
    "Northwest Territories", "Nunavut", "Prince Edward Island", "Quebec", "Québec", "Saskatchewan", "Yukon",
])  # fmt: skip
def test_another_province_settles_a_shared_town_name(province: str) -> None:
    assert where([f"Killarney, {province}"], country="CA") == "elsewhere"
    assert where([f"Cochrane, {province}, Canada"]) == "elsewhere"
    assert where([f"Georgetown, {province}"]) == "elsewhere"


@pytest.mark.parametrize("state", [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
    "District of Columbia", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas",
    "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri",
    "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina",
    "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming",
])  # fmt: skip
def test_a_us_state_after_canada_makes_it_a_town(state: str) -> None:
    assert where([f"Canada, {state}, US"]) == "elsewhere"
    assert where([f"Canada, {state}, US"], country="US") == "elsewhere"


def test_vague() -> None:
    assert vague("Remote") and vague("Hybrid") and vague("") and vague(None)
    assert not vague("Toronto, ON")
