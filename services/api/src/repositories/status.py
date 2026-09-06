from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from queries.status import WAREHOUSE_STATUS


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class StatusRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_status(self) -> dict:
        row = dict(self.db.execute(WAREHOUSE_STATUS).mappings().one())
        return {
            "last_scraped_at": as_utc(row.get("last_scraped_at")),
            "player_count": int(row.get("player_count") or 0),
            "game_count": int(row.get("game_count") or 0),
            "season_count": int(row.get("season_count") or 0),
            "first_season": row.get("first_season"),
            "last_season": row.get("last_season"),
        }
