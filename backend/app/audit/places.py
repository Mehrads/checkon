"""Where a board posting's work is: in Ontario, somewhere in Canada that may be Ontario (remote or Canada-wide), or
elsewhere. Read from the board's location fields, never the posting text, so it costs nothing to decide.

Many Ontario place names are also places elsewhere (London, Hamilton, Waterloo, Windsor…). On its own, only a
short list of names that mean Ontario counts; any Ontario place counts when the location also says Canada.
"""

import csv
import re
from functools import cache
from typing import Literal

from app.pay.jobbank import DATA_DIR

Where = Literal["ontario", "canada", "elsewhere"]

# Names that mean a place in Ontario without saying so
ONTARIO_CITIES = {
    "toronto", "ottawa", "mississauga", "brampton", "markham", "vaughan", "kitchener", "oakville", "oshawa", "barrie",
    "guelph", "sudbury", "greater sudbury", "thunder bay", "whitby", "ajax", "pickering", "etobicoke", "scarborough",
    "north york", "east york", "kanata", "nepean", "orleans", "newmarket", "aurora", "sault ste marie",
    "sault ste. marie", "st. catharines", "st catharines", "niagara falls", "brantford", "sarnia", "welland",
    "timmins", "north bay", "orillia", "belleville", "kitchener-waterloo", "kitchener waterloo", "waterloo region",
    "gta", "greater toronto area", "greater toronto", "richmond hill", "woodbridge", "bolton", "caledon", "halton hills",
    "georgetown", "stoney creek", "ancaster", "dundas", "collingwood", "cobourg", "bowmanville", "clarington",
}  # fmt: skip

_CITY = re.compile(r"\b(?:" + "|".join(map(re.escape, sorted(ONTARIO_CITIES, key=len, reverse=True))) + r")\b", re.I)
_ONTARIO = re.compile(r"\bontario\b|\bont\b\.?", re.IGNORECASE)
_ON = re.compile(r"(?:^|[\s,(/;|])ON(?=$|[\s,)/;|.])")
# Another country, or a US state after a comma: "Ottawa, IL" is in Illinois
_ABROAD = re.compile(
    r"(?i:\b(?:united states|usa|u\.s\.a?\.?|united kingdom|uk|england|australia|india|ireland)\b)"
    r"|,\s*(?:A[KLRZ]|C[AOT]|D[CE]|FL|GA|HI|I[ADLN]|K[SY]|LA|M[ADEINOST]|N[CDEHJMVY]|O[HKR]|PA|RI|S[CD]|T[NX]|UT|V[AT]"
    r"|W[AIVY])\b",
)
_CANADA = re.compile(r"\bcanada\b|\bcanadian\b", re.IGNORECASE)
_OTHER_PROVINCE = re.compile(
    r"\b(?:british columbia|alberta|saskatchewan|manitoba|qu[ée]bec|nova scotia|new brunswick|newfoundland|labrador"
    r"|prince edward island|yukon|northwest territories|nunavut|vancouver|burnaby|victoria|kelowna|calgary|edmonton"
    r"|regina|saskatoon|winnipeg|montr[ée]al|laval|gatineau|halifax|moncton|fredericton|st\.? john's|charlottetown)\b"
    r"|(?:^|[\s,(/;|])(?-i:BC|AB|SK|MB|QC|PQ|NS|NB|NL|PE|PEI|YT|NT|NU)(?=$|[\s,)/;|.])",
    re.IGNORECASE,
)
_SEGMENT = re.compile(r"\s*(?:[,;/|()]|\s-\s|\s–\s)\s*")
_NOISE = re.compile(
    r"\b(?:remote|hybrid|on-?site|in[- ]office|office|onsite|flexible|area|region|metro|downtown|headquarters|hq)\b",
    re.IGNORECASE,
)
_CANADA_CODES = {"ca", "can", "canada"}


@cache
def ontario_places() -> frozenset[str]:
    """Every Ontario census subdivision and the place names Job Bank's postings use, lower-cased."""
    with (DATA_DIR / "ontario_places.csv").open(encoding="utf-8", newline="") as f:
        return frozenset(row["place"] for row in csv.DictReader(f))


def _segments(location: str) -> list[str]:
    parts = (_NOISE.sub(" ", part).strip(" .-").lower() for part in _SEGMENT.split(location))
    return [" ".join(part.split()) for part in parts if part.strip()]


def _in_ontario(location: str, canada: bool) -> bool:
    if _ONTARIO.search(location) or _ON.search(location):
        return True
    if _CITY.search(location) and not _ABROAD.search(location):
        return True
    return canada and any(segment in ontario_places() for segment in _segments(location))


def where(locations: list[str], *, remote: bool = False, country: str | None = None) -> Where:
    """`country` is a structured country field (a code such as "CA", or a name), which settles names like London.
    `remote` marks a posting open to anywhere in its country. A Canada-wide posting may be filled in Ontario."""
    in_canada = (country or "").strip().lower() in _CANADA_CODES
    texts = [location for location in locations if location and location.strip()]
    if any(_in_ontario(location, in_canada or bool(_CANADA.search(location))) for location in texts):
        return "ontario"
    if any(_CANADA.search(location) and not _OTHER_PROVINCE.search(location) for location in texts):
        return "canada"  # "Remote - Canada", "Canada", "US or Canada"
    if in_canada and (remote or not texts):
        return "canada"
    return "elsewhere"


def vague(location: str | None) -> bool:
    """A location that names no place, such as "Remote" or "Hybrid"."""
    return not _segments(location or "")
