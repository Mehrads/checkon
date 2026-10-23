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
    (["New York City, NY; San Francisco, CA"], {}, "elsewhere"),
    (["Remote - US"], {}, "elsewhere"),
    (["Remote"], {}, "elsewhere"),
    (["Sydney"], {"country": "AU", "remote": True}, "elsewhere"),
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


def test_vague() -> None:
    assert vague("Remote") and vague("Hybrid") and vague("") and vague(None)
    assert not vague("Toronto, ON")
