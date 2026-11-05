"""Refresh the Job Bank files in app/pay/data/ from the Government of Canada's open data:

    uv run python -m app.pay.refresh

Downloads the newest year of Job Bank's "Wages" dataset (open.canada.ca, Open Government Licence – Canada) and
keeps Ontario's rows. Then rebuilds the place names that put a job location in its economic region: Statistics
Canada's census subdivisions (SGC 2021), each in its census division's economic region, plus the city names on
the latest month of Job Bank's own postings, which also record each posting's economic region. Where Job Bank
consistently places a city differently (Burlington: Hamilton–Niagara Peninsula), Job Bank's placement wins, so
the wages shown are the ones Job Bank shows for that city.

Job Bank publishes new wages once a year, usually in November or December. Review the diff and commit it.
"""

import csv
import io
import json
import logging
import re
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

from app.pay.jobbank import DATA_DIR, ONTARIO, plain

CKAN = "https://open.canada.ca/data/api/action/package_show"
WAGES_DATASET = "adad580f-76b0-4502-bd05-20c125de9116"
POSTINGS_DATASET = "ea639e28-c0fc-48bf-b5dd-b8899bd43072"
DATASET_PAGE = "https://open.canada.ca/data/en/dataset/{id}"
SGC_STRUCTURE = "https://www.statcan.gc.ca/en/statistical-programs/document/sgc-cgt-2021-structure-eng.csv"
LICENCE_URL = "https://open.canada.ca/en/open-government-licence-canada"

# Ontario's economic regions by census division (Statistics Canada, SGC 2021): each region is whole divisions.
ECONOMIC_REGIONS = {
    "ER3510": [3501, 3502, 3506, 3507, 3509],  # Ottawa
    "ER3515": [3510, 3511, 3512, 3513, 3547],  # Kingston–Pembroke
    "ER3520": [3514, 3515, 3516, 3544, 3546],  # Muskoka–Kawarthas
    "ER3530": [3518, 3519, 3520, 3521, 3524],  # Toronto
    "ER3540": [3522, 3523, 3530, 3543],  # Kitchener–Waterloo–Barrie
    "ER3550": [3525, 3526, 3528, 3529],  # Hamilton–Niagara Peninsula
    "ER3560": [3532, 3534, 3539],  # London
    "ER3570": [3536, 3537, 3538],  # Windsor–Sarnia
    "ER3580": [3531, 3540, 3541, 3542],  # Stratford–Bruce Peninsula
    "ER3590": [3548, 3549, 3551, 3552, 3553, 3554, 3556, 3557],  # Northeast
    "ER3595": [3558, 3559, 3560],  # Northwest
}
DIVISION_REGION = {division: region for region, divisions in ECONOMIC_REGIONS.items() for division in divisions}
# A city name on Job Bank's postings counts when it has this many Ontario postings, nearly all in one region.
MIN_POSTINGS = 5
MIN_SHARE = 0.8

logger = logging.getLogger(__name__)

WAGE_FIELDS = ["noc", "region", "low", "q1", "median", "q3", "high", "unit", "source", "period"]


def _get(client: httpx.Client, url: str, **params: str) -> httpx.Response:
    response = client.get(url, params=params or None, follow_redirects=True, timeout=300)
    response.raise_for_status()
    return response


def _package(client: httpx.Client, dataset: str) -> dict[str, Any]:
    package: dict[str, Any] = _get(client, CKAN, id=dataset).json()["result"]
    return package


def _amount(value: str) -> str:
    """The figure as Job Bank gives it, or "" when it isn't published."""
    value = value.strip()
    return str(Decimal(value)) if value and value.upper() != "NA" else ""


def wages(client: httpx.Client) -> tuple[dict[str, Any], list[dict[str, str]]]:
    package = _package(client, WAGES_DATASET)
    yearly = [r for r in package["resources"] if r["format"] == "CSV" and re.match(r"\d{4} Wages", r["name"].strip())]
    resource = max(yearly, key=lambda r: r["name"].strip()[:4])
    logger.info(f"Wages: {resource['name'].strip()} from {resource['url']}")
    text = _get(client, resource["url"]).content.decode("utf-8-sig")
    rows = [row for row in csv.DictReader(io.StringIO(text)) if row["prov"] == "ON"]
    occupations: dict[str, str] = {}
    regions: dict[str, str] = {}
    kept = []
    for row in rows:
        noc = row["NOC_CNP"].removeprefix("NOC_")
        occupations[noc] = row["NOC_Title_eng"].strip()
        regions[row["ER_Code_Code_RE"]] = row["ER_Name"].strip().replace("--", "–")
        figures = {
            "low": _amount(row["Low_Wage_Salaire_Minium"]), "q1": _amount(row["Quartile1_Wage_Salaire_Quartile1"]),
            "median": _amount(row["Median_Wage_Salaire_Median"]), "q3": _amount(row["Quartile3_Wage_Salaire_Quartile3"]),
            "high": _amount(row["High_Wage_Salaire_Maximal"]),
        }  # fmt: skip
        if not any(figures.values()):  # "Due to data limitations, the wage for this occupation cannot be published"
            continue
        kept.append({
            "noc": noc, "region": row["ER_Code_Code_RE"], **figures,
            "unit": "year" if row["Annual_Wage_Flag_Salaire_annuel"].strip() == "1" else "hour",
            "source": row["Data_Source_E"].strip(), "period": row["Reference_Period"].strip(),
        })  # fmt: skip
    published = max(row["Revision_Date_Date_revision"].strip() for row in rows)
    year = resource["name"].strip()[:4]
    meta = {
        "dataset": {
            "title": f"Job Bank wages, {year}",
            "publisher": "Employment and Social Development Canada",
            "url": DATASET_PAGE.format(id=WAGES_DATASET),
            "resource_url": resource["url"],
            "licence": package.get("license_title") or "Open Government Licence - Canada",
            "licence_url": LICENCE_URL,
            "published": published,
            "refreshed": datetime.now(UTC).date().isoformat(),
        },
        "regions": dict(sorted(regions.items())),
        "occupations": dict(sorted(occupations.items())),
    }
    kept.sort(key=lambda row: (row["noc"], row["region"]))
    logger.info(f"  {len(occupations)} occupations, {len(regions)} regions, {len(kept)} rows with figures, published {published}")
    return meta, kept


def census_places(client: httpx.Client) -> dict[str, set[str]]:
    """Ontario's census subdivisions by name, each with its economic region(s): "Hamilton" is a city and a township."""
    text = _get(client, SGC_STRUCTURE).content.decode("cp1252")
    places: dict[str, set[str]] = defaultdict(set)
    for row in csv.reader(text.splitlines()[1:]):
        level, code, title = row[1], row[2], row[3]
        if level != "Census subdivision" or not code.startswith("35"):
            continue
        for name in title.split(" / "):  # bilingual names
            places[plain(name)].add(DIVISION_REGION[int(code[:4])])
    return places


def posting_places(client: httpx.Client, regions: dict[str, str]) -> tuple[dict[str, Counter[str]], str]:
    """Ontario city names on the latest month of Job Bank postings, with the regions Job Bank gave them."""
    package = _package(client, POSTINGS_DATASET)
    english = [r for r in package["resources"] if r["format"] == "CSV" and re.search(r"-en-[a-z]+\d{4}\.csv$", r["url"])]
    resource = max(english, key=lambda r: r.get("created") or "")
    logger.info(f"Postings: {resource['name'].strip()} from {resource['url']}")
    by_name = {plain(name): code for code, name in regions.items()}
    cities: dict[str, Counter[str]] = defaultdict(Counter)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "postings.csv"
        path.write_bytes(_get(client, resource["url"]).content)
        with path.open(encoding="utf-16", newline="") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                if row.get("Province/Territory") not in ("Ontario", "ON"):
                    continue
                region = by_name.get(plain(re.sub(r"\s+Region$", "", row.get("Economic  Region") or "")))
                city = plain(row.get("City") or "")
                if region and city:
                    cities[city][region] += 1
    return cities, resource["name"].strip()


def places(census: dict[str, set[str]], postings: dict[str, Counter[str]]) -> dict[str, str]:
    found = {name: next(iter(found)) for name, found in census.items() if len(found) == 1}
    agree = total = 0
    for city, counts in postings.items():
        region, count = counts.most_common(1)[0]
        n = sum(counts.values())
        if city in found:
            total += n
            agree += counts[found[city]]
        if n >= MIN_POSTINGS and count / n >= MIN_SHARE and found.get(city) != region:
            logger.info(f"  {city}: {found.get(city, 'not a census subdivision')} -> {region} ({count} of {n} postings)")
            found[city] = region
    logger.info(f"  census regions agree with Job Bank on {agree} of {total} postings in census subdivisions")
    return dict(sorted(found.items()))


def write(meta: dict[str, Any], rows: list[dict[str, str]], where: dict[str, str], directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "job_bank.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (directory / "job_bank_wages.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, WAGE_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with (directory / "ontario_places.csv").open("w", encoding="utf-8", newline="") as f:
        table = csv.writer(f, lineterminator="\n")
        table.writerow(["place", "region"])
        table.writerows(where.items())


def main(directory: Path = DATA_DIR) -> None:
    with httpx.Client(headers={"User-Agent": "CheckON wage refresh (https://github.com/Mehrads/checkon)"}) as client:
        meta, rows = wages(client)
        census = census_places(client)
        postings, month = posting_places(client, meta["regions"])
    where = places(census, postings)
    assert ONTARIO in meta["regions"] and set(where.values()) <= set(meta["regions"]), "unexpected region codes"
    meta["dataset"]["places_from"] = f"Statistics Canada SGC 2021; Job Bank postings, {month}"
    write(meta, rows, where, directory)
    logger.info(f"Wrote {len(rows)} wage rows and {len(where)} place names to {directory}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_DIR)
