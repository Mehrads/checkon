"""Job Bank wages by occupation (NOC 2021) and economic region, from the Government of Canada's open data
(Technical Design §9, source 3). Every figure comes from the downloaded dataset, never from a model.

Ontario's rows live in versioned files in data/, written by `python -m app.pay.refresh` when Job Bank publishes
a new year. A job location is placed in its economic region by name: Statistics Canada's census subdivisions,
plus the place names Job Bank's own postings use, such as "North York" or "Kanata" (data/ontario_places.csv).
"""

import csv
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from functools import cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.compliance.models import PayUnit

DATA_DIR = Path(__file__).resolve().parent / "data"
ONTARIO = "ER35"  # the province as a whole: used when the location isn't a known place

_ASIDES = re.compile(r"\([^)]*\)|\[[^\]]*\]")  # "(hybrid)", "[remote]"
_SEGMENTS = re.compile(r"[,;|/\n]|\s[-–—]\s")
_LONGEST_PLACE = 5  # words


class Dataset(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str  # "Job Bank wages, 2025"
    publisher: str
    url: str  # the dataset's page on open.canada.ca
    resource_url: str  # the file that was downloaded
    licence: str
    licence_url: str
    published: date  # Job Bank's revision date for the figures
    refreshed: date  # when the file was downloaded
    places_from: str  # the sources of the place names


class Wage(BaseModel):
    """One occupation in one region. Job Bank's low and high wages are the 10th and 90th percentiles."""

    model_config = ConfigDict(frozen=True)

    noc: str
    region: str
    low: Decimal | None
    q1: Decimal | None
    median: Decimal | None
    q3: Decimal | None
    high: Decimal | None
    unit: PayUnit  # hour, or year where Job Bank shows the occupation at an annual rate
    source: str  # "Labour Force Survey", "2021 Census"…
    period: str  # the reference period, "2023-2024"


def plain(text: str) -> str:
    """Lower case without accents or punctuation: "Orléans" and "orleans" are one place."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


@dataclass(frozen=True)
class JobBank:
    dataset: Dataset
    occupations: dict[str, str]  # NOC code -> title
    regions: dict[str, str]  # economic region code -> name
    wages: dict[tuple[str, str], Wage]  # (NOC code, region code)
    places: dict[str, str]  # plain(name) -> region code

    def wage(self, noc: str, region: str) -> Wage | None:
        """The region's figures, or Ontario's when Job Bank publishes no median for the region."""
        for code in dict.fromkeys((region, ONTARIO)):
            found = self.wages.get((noc, code))
            if found is not None and found.median is not None:
                return found
        return None

    def region_for(self, location: str | None) -> str:
        """The economic region of a job location such as "North York, Toronto, ON (hybrid)". A part that is
        exactly a place wins over a place inside a longer part ("123 King Street, Toronto" is Toronto, not King
        Township); an unknown or remote location is Ontario as a whole."""
        parts = [plain(part) for part in _SEGMENTS.split(_ASIDES.sub(" ", location or ""))]
        parts = [part for part in parts if part]
        for part in parts:
            if part in self.places:
                return self.places[part]
        for part in parts:
            words = part.split()
            for size in range(min(len(words), _LONGEST_PLACE), 0, -1):
                for start in range(len(words) - size + 1):
                    if (found := self.places.get(" ".join(words[start : start + size]))) is not None:
                        return found
        return ONTARIO


def _amount(value: str) -> Decimal | None:
    return Decimal(value) if value else None


@cache
def load_job_bank(directory: Path = DATA_DIR) -> JobBank:
    meta = json.loads((directory / "job_bank.json").read_text(encoding="utf-8"))
    with (directory / "job_bank_wages.csv").open(encoding="utf-8", newline="") as f:
        wages = {
            (row["noc"], row["region"]): Wage(
                noc=row["noc"], region=row["region"], low=_amount(row["low"]), q1=_amount(row["q1"]),
                median=_amount(row["median"]), q3=_amount(row["q3"]), high=_amount(row["high"]),
                unit=PayUnit(row["unit"]), source=row["source"], period=row["period"],
            )
            for row in csv.DictReader(f)
        }  # fmt: skip
    with (directory / "ontario_places.csv").open(encoding="utf-8", newline="") as f:
        places = {row["place"]: row["region"] for row in csv.DictReader(f)}
    return JobBank(
        dataset=Dataset(**meta["dataset"]), occupations=meta["occupations"], regions=meta["regions"],
        wages=wages, places=places,
    )  # fmt: skip
