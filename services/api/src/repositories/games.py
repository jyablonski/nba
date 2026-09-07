from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from queries.games import (
    GAME_EXISTS,
    GET_GAME_FLOW,
    LIST_GAMES,
    LIST_GAMES_COUNT,
    LIST_PLAY_BY_PLAY,
    LIST_SCHEDULE,
    LIST_SCHEDULE_COUNT,
    LIST_SEASONS,
)


class GamesRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_games(
        self,
        *,
        season: str | None,
        season_type: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[int, list[dict]]:
        params = {
            "season": season,
            "season_type": season_type,
            "limit": limit,
            "offset": offset,
        }
        total = self.db.execute(LIST_GAMES_COUNT, params).scalar_one()
        rows = self.db.execute(LIST_GAMES, params)
        return int(total), [dict(row._mapping) for row in rows]

    def list_schedule(
        self,
        *,
        season: str | None,
        status: str | None,
        from_date: date,
        limit: int,
        offset: int,
    ) -> tuple[int, list[dict]]:
        params = {
            "season": season,
            "status": status,
            "from_date": from_date,
            "limit": limit,
            "offset": offset,
        }
        total = self.db.execute(LIST_SCHEDULE_COUNT, params).scalar_one()
        rows = self.db.execute(LIST_SCHEDULE, params)
        return int(total), [dict(row._mapping) for row in rows]

    def list_seasons(self) -> list[str]:
        rows = self.db.execute(LIST_SEASONS)
        return [row[0] for row in rows]

    def game_exists(self, game_id: UUID) -> bool:
        value = self.db.execute(GAME_EXISTS, {"game_id": game_id}).scalar()
        return bool(value)

    def list_play_by_play(self, game_id: UUID) -> list[dict]:
        rows = self.db.execute(LIST_PLAY_BY_PLAY, {"game_id": game_id})
        return [dict(row._mapping) for row in rows]

    def get_game_flow(self, game_id: UUID) -> dict | None:
        row = self.db.execute(GET_GAME_FLOW, {"game_id": game_id}).first()
        if row is None:
            return None
        payload = dict(row._mapping)
        payload["has_play_by_play"] = payload.get("scoring_play_count") is not None
        return payload
