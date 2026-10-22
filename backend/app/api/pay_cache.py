"""The postings search behind pay suggestions (app/pay/suggest.py) in Postgres, kept a week so repeat suggestions
for the same job title and place don't search again. Rows hold quoted pay and links; never posting text.
"""

from datetime import timedelta

from pydantic import ValidationError
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, col, delete, select

from app.models import PayPostingSearch, get_datetime_utc
from app.pay.suggest import SEARCH_DAYS, PostingSearch

KEPT = timedelta(days=SEARCH_DAYS)


class PostgresPostingCache:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, key: tuple[str, str]) -> PostingSearch | None:
        title, location = key
        row = self.session.exec(select(PayPostingSearch).where(
            PayPostingSearch.title == title, PayPostingSearch.location == location,
            PayPostingSearch.searched_at > get_datetime_utc() - KEPT,
        )).first()  # fmt: skip
        if row is None:
            return None
        try:
            return PostingSearch.model_validate(row.result)
        except ValidationError:  # stored before PostingSearch changed: search again
            return None

    def put(self, key: tuple[str, str], value: PostingSearch) -> None:
        title, location = key
        now = get_datetime_utc()
        self.session.exec(delete(PayPostingSearch).where(col(PayPostingSearch.searched_at) <= now - KEPT))
        result = value.model_dump(mode="json")
        upsert = insert(PayPostingSearch).values(title=title, location=location, result=result, searched_at=now)
        upsert = upsert.on_conflict_do_update(
            index_elements=["title", "location"], set_={"result": result, "searched_at": now}
        )
        self.session.exec(upsert)
        self.session.commit()
