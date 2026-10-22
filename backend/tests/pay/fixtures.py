"""A small Job Bank dataset for tests, written like the refresh command writes the real one, so tests don't change
when Job Bank publishes new figures."""

import json
from pathlib import Path

from app.pay.jobbank import JobBank, load_job_bank

DATASET = {
    "title": "Job Bank wages, 2025",
    "publisher": "Employment and Social Development Canada",
    "url": "https://open.canada.ca/data/en/dataset/adad580f-76b0-4502-bd05-20c125de9116",
    "resource_url": "https://open.canada.ca/data/dataset/adad580f/resource/9da94d63/download/wages2025.csv",
    "licence": "Open Government Licence - Canada",
    "licence_url": "https://open.canada.ca/en/open-government-licence-canada",
    "published": "2025-11-19",
    "refreshed": "2026-10-22",
    "places_from": "Statistics Canada SGC 2021; Job Bank postings, September 2026",
}
OCCUPATIONS = {
    "00010": "Legislators",
    "13100": "Administrative officers",
    "13102": "Payroll administrators",
    "21232": "Software developers and programmers",
    "99000": "An occupation without published wages",
}
REGIONS = {"ER35": "Ontario", "ER3510": "Ottawa", "ER3530": "Toronto", "ER3595": "Northwest"}
WAGES = """noc,region,low,q1,median,q3,high,unit,source,period
00010,ER35,37561,52000,80000,134000,186000,year,2021 Census,2021
00010,ER3595,,,,,,year,2021 Census,2021
13100,ER3530,21,25,30,35,40,hour,Labour Force Survey,2023-2024
13102,ER35,19.23,24.04,30,38.46,44.41,hour,Labour Force Survey,2023-2024
13102,ER3510,21,25,32,39,45,hour,Labour Force Survey,2023-2024
13102,ER3530,20,24.04,31.25,40.38,46.96,hour,Labour Force Survey,2023-2024
21232,ER3530,30,30,48.08,60,76.92,hour,Labour Force Survey,2023-2024
"""
PLACES = """place,region
kanata,ER3510
king,ER3510
mississauga,ER3530
north york,ER3530
ottawa,ER3510
thunder bay,ER3595
toronto,ER3530
"""


def write_job_bank(directory: Path) -> JobBank:
    directory.mkdir(parents=True, exist_ok=True)
    meta = {"dataset": DATASET, "regions": REGIONS, "occupations": OCCUPATIONS}
    (directory / "job_bank.json").write_text(json.dumps(meta), encoding="utf-8")
    (directory / "job_bank_wages.csv").write_text(WAGES, encoding="utf-8")
    (directory / "ontario_places.csv").write_text(PLACES, encoding="utf-8")
    return load_job_bank(directory)
