"""Scrape LeagueStandingsV3 into source.standings (Regular Season, season-to-date)."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from sqlalchemy import func

from db import get_session, upsert_rows
from models import Standing, Team
from scrapers import (
    NBA_REQUEST_TIMEOUT,
    dataset_rows,
    nba_call,
    row_get,
    to_float,
    to_int,
    to_str,
)
from scrapers.teams import scrape_teams

logger = logging.getLogger(__name__)

SEASON_TYPE = "Regular Season"


def _ensure_teams() -> None:
    with get_session() as session:
        count = session.query(func.count(Team.team_id)).scalar() or 0
    if count == 0:
        logger.info("No teams in source.teams; scraping teams first")
        scrape_teams()


def _known_team_ids() -> set[int]:
    with get_session() as session:
        return {tid for (tid,) in session.query(Team.team_id).all()}


def _parse_games_back(value: Any) -> float | None:
    """GB '-' or empty means the conference/division leader (0.0)."""
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text == "-":
        return 0.0
    return to_float(value)


def _row_to_standing(
    row: dict[str, Any],
    *,
    season: str,
    as_of: date,
    scraped_at: datetime,
    known_team_ids: set[int],
) -> dict[str, Any] | None:
    team_id = to_int(row_get(row, "TeamID"))
    if team_id is None or team_id not in known_team_ids:
        return None

    raw_gb = row_get(row, "GB", "GamesBack")
    games_back = _parse_games_back(raw_gb)
    if games_back is None and raw_gb is None:
        games_back = _parse_games_back(row_get(row, "ConferenceGamesBack"))

    return {
        "team_id": team_id,
        "season": season,
        "season_type": SEASON_TYPE,
        "as_of_date": as_of,
        "conference": to_str(row_get(row, "Conference")),
        "division": to_str(row_get(row, "Division")),
        "conference_rank": to_int(row_get(row, "PlayoffRank", "ConferenceRank")),
        "division_rank": to_int(row_get(row, "DivisionRank")),
        "wins": to_int(row_get(row, "WINS")),
        "losses": to_int(row_get(row, "LOSSES")),
        "win_pct": to_float(row_get(row, "WinPCT")),
        "games_back": games_back,
        "conf_games_back": _parse_games_back(row_get(row, "ConferenceGamesBack")),
        "streak": to_str(row_get(row, "strCurrentStreak", "CurrentStreak")),
        "last_10": to_str(row_get(row, "L10", "LTen")),
        "scraped_at": scraped_at,
    }


def _league_standings(season: str) -> list[dict]:
    from nba_api.stats.endpoints.leaguestandingsv3 import LeagueStandingsV3

    endpoint = nba_call(
        lambda: LeagueStandingsV3(
            season=season,
            season_type=SEASON_TYPE,
            league_id="00",
            timeout=NBA_REQUEST_TIMEOUT,
        )
    )
    return dataset_rows(endpoint.get_normalized_dict(), "Standings")


def scrape_standings(season: str, *, as_of: date | None = None) -> int:
    """Upsert Regular Season standings for ``season``. ``as_of`` defaults to today."""
    _ensure_teams()
    known = _known_team_ids()
    as_of_date = as_of or date.today()
    scraped_at = datetime.now()

    rows = _league_standings(season)
    records = [
        rec
        for rec in (
            _row_to_standing(
                row,
                season=season,
                as_of=as_of_date,
                scraped_at=scraped_at,
                known_team_ids=known,
            )
            for row in rows
        )
        if rec is not None
    ]
    with get_session() as session:
        written = upsert_rows(session, Standing, records, ["season", "season_type", "team_id"])
    logger.info("Upserted %s standings rows for season %s", written, season)
    return written
