"""The employer-size search cache (app/compliance/employer.py) in Postgres, so cold starts and deploys keep it.
Rows hold the search's figures, summary and source, keyed by employer and job location; never posting text.
"""

from datetime import timedelta

from pydantic import ValidationError
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, col, delete, select

from app.compliance.employer import CACHE_SECONDS, EmployerSize
from app.models import EmployerSizeSearch, get_datetime_utc

KEPT = timedelta(seconds=CACHE_SECONDS)
MAX_KEY = 255  # the column width; longer names and locations aren't cached


class PostgresSizeCache:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, key: tuple[str, str]) -> EmployerSize | None:
        employer, location = key
        row = self.session.exec(select(EmployerSizeSearch).where(
            EmployerSizeSearch.employer == employer, EmployerSizeSearch.location == location,
            EmployerSizeSearch.searched_at > get_datetime_utc() - KEPT,
        )).first()  # fmt: skip
        if row is None:
            return None
        try:
            return EmployerSize.model_validate(row.size)
        except ValidationError:  # stored before EmployerSize changed: search again
            return None

    def put(self, key: tuple[str, str], value: EmployerSize) -> None:
        employer, location = key
        if len(employer) > MAX_KEY or len(location) > MAX_KEY:
            return
        now = get_datetime_utc()
        self.session.exec(delete(EmployerSizeSearch).where(col(EmployerSizeSearch.searched_at) <= now - KEPT))
        size = value.model_dump(mode="json")
        upsert = insert(EmployerSizeSearch).values(employer=employer, location=location, size=size, searched_at=now)
        upsert = upsert.on_conflict_do_update(
            index_elements=["employer", "location"], set_={"size": size, "searched_at": now}
        )
        self.session.exec(upsert)
        self.session.commit()
