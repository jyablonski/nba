"""Scrape per-player per-game stat lines into source.player_game_logs."""

from __future__ import annotations

import logging
from datetime import date, datetime

from sqlalchemy import func, or_

from db import get_session, upsert_rows
from models import Game, Player, PlayerGameLog, Team
from scrapers import (
    LOG_SEASON_TYPES,
    NBA_REQUEST_TIMEOUT,
    current_season,
    dataset_rows,
    matchup_team_abbr,
    nba_call,
    nba_date,
    parse_game_date,
    parse_minutes,
    row_get,
    season_start_year,
    to_float,
    to_int,
    to_str,
)
from scrapers.players import scrape_players, upsert_player_stubs
from scrapers.teams import resolve_team_id, scrape_teams, team_id_by_abbreviation

logger = logging.getLogger(__name__)


def scrape_player_game_logs(season: str, *, active_only: bool = False) -> int:
    _ensure_reference_data(season)
    player_ids = _player_ids_for_season(season, active_only=active_only)
    if not active_only and not player_ids:
        player_ids = _static_player_ids(active_only=False)
        upsert_player_stubs(
            [{"player_id": pid, "full_name": "", "is_active": False} for pid in player_ids]
        )
        player_ids = _player_ids_for_season(season, active_only=False)

    known_game_ids = _game_ids_for_season(season)
    abbr_map: dict[str, int] = {}
    with get_session() as session:
        abbr_map = team_id_by_abbreviation(session)

    scraped_at = datetime.now()
    total = 0
    for index, player_id in enumerate(player_ids, start=1):
        rows: list[dict] = []
        for season_type in LOG_SEASON_TYPES:
            try:
                api_rows = _player_game_log(player_id, season, season_type)
            except Exception:
                logger.warning(
                    "PlayerGameLog failed player_id=%s season=%s type=%s",
                    player_id,
                    season,
                    season_type,
                )
                continue
            for raw in api_rows:
                mapped = _map_player_game_log(
                    raw,
                    season=season,
                    team_abbr_map=abbr_map,
                    scraped_at=scraped_at,
                    known_game_ids=known_game_ids,
                )
                if mapped:
                    rows.append(mapped)
        if rows:
            with get_session() as session:
                total += upsert_rows(session, PlayerGameLog, rows, ["player_id", "game_id"])
        if index % 25 == 0 or index == len(player_ids):
            logger.info(
                "Game logs %s/%s players for %s (%s rows so far)",
                index,
                len(player_ids),
                season,
                total,
            )
    return total


def scrape_logs_for_games(games: list[dict], today: date | None = None) -> int:
    """Incremental logs for a set of completed games (used by scrape-daily)."""
    if not games:
        return 0
    today = today or date.today()
    season = games[0].get("season") or current_season(today)
    _ensure_teams()

    game_ids = {game["game_id"] for game in games}
    scraped_at = datetime.now()
    api_rows: list[dict] = []
    try:
        api_rows = _player_game_logs_for_date(season, today)
    except Exception:
        logger.warning("PlayerGameLogs date query failed; falling back to box scores")

    if not api_rows:
        for game in games:
            try:
                api_rows.extend(_box_score_player_stats(game["game_id"]))
            except Exception:
                logger.warning("BoxScoreTraditionalV2 failed for game_id=%s", game["game_id"])

    abbr_map: dict[str, int] = {}
    with get_session() as session:
        abbr_map = team_id_by_abbreviation(session)

    stubs: list[dict] = []
    mapped_rows: list[dict] = []
    for raw in api_rows:
        game_id = to_str(row_get(raw, "GAME_ID", "Game_ID"))
        if game_id and game_ids and game_id not in game_ids:
            continue
        player_id = to_int(row_get(raw, "PLAYER_ID", "Player_ID"))
        if player_id is None:
            continue
        stubs.append(
            {
                "player_id": player_id,
                "full_name": to_str(row_get(raw, "PLAYER_NAME", "DISPLAY_FIRST_LAST")) or "",
                "is_active": True,
            }
        )
        mapped = _map_player_game_log(
            raw,
            season=season,
            team_abbr_map=abbr_map,
            scraped_at=scraped_at,
            known_game_ids=game_ids or None,
        )
        if mapped:
            mapped_rows.append(mapped)

    if stubs:
        upsert_player_stubs(stubs)
    if not mapped_rows:
        return 0
    with get_session() as session:
        written = upsert_rows(session, PlayerGameLog, mapped_rows, ["player_id", "game_id"])
    logger.info("Upserted %s player game logs for %s games", written, len(game_ids))
    return written


def _ensure_teams() -> None:
    with get_session() as session:
        count = session.query(func.count(Team.team_id)).scalar() or 0
    if count == 0:
        scrape_teams()


def _ensure_reference_data(season: str) -> None:
    _ensure_teams()
    with get_session() as session:
        player_count = session.query(func.count(Player.player_id)).scalar() or 0
        game_count = (
            session.query(func.count(Game.game_id)).filter(Game.season == season).scalar() or 0
        )
    if player_count == 0:
        logger.info("No players in source.players; scraping players first")
        scrape_players(enrich=False)
    if game_count == 0:
        logger.info("No games for %s; scraping games first", season)
        from scrapers.games import scrape_games

        scrape_games(season)


def _player_ids_for_season(season: str, *, active_only: bool) -> list[int]:
    start_year = season_start_year(season)
    with get_session() as session:
        query = session.query(Player.player_id)
        if active_only:
            query = query.filter(Player.is_active.is_(True))
        else:
            query = query.filter(
                or_(Player.to_year.is_(None), Player.to_year >= start_year),
                or_(Player.from_year.is_(None), Player.from_year <= start_year + 1),
            )
        ids = [row[0] for row in query.all()]
    if active_only and not ids:
        ids = _static_player_ids(active_only=True)
        from nba_api.stats.static import players as static_players

        stubs = [
            {
                "player_id": player["id"],
                "first_name": player.get("first_name"),
                "last_name": player.get("last_name"),
                "full_name": player.get("full_name"),
                "is_active": True,
            }
            for player in static_players.get_active_players()
        ]
        upsert_player_stubs(stubs)
    return ids


def _static_player_ids(*, active_only: bool) -> list[int]:
    from nba_api.stats.static import players as static_players

    source = static_players.get_active_players() if active_only else static_players.get_players()
    return [int(player["id"]) for player in source]


def _game_ids_for_season(season: str) -> set[str]:
    with get_session() as session:
        return {row[0] for row in session.query(Game.game_id).filter(Game.season == season).all()}


def _player_game_log(player_id: int, season: str, season_type: str) -> list[dict]:
    from nba_api.stats.endpoints import playergamelog

    endpoint = nba_call(
        lambda: playergamelog.PlayerGameLog(
            player_id=player_id,
            season=season,
            season_type_all_star=season_type,
            timeout=NBA_REQUEST_TIMEOUT,
        )
    )
    return dataset_rows(endpoint.get_normalized_dict(), "PlayerGameLog")


def _player_game_logs_for_date(season: str, day: date) -> list[dict]:
    from nba_api.stats.endpoints import playergamelogs

    rows: list[dict] = []
    for season_type in LOG_SEASON_TYPES:
        try:
            endpoint = nba_call(
                lambda st=season_type: playergamelogs.PlayerGameLogs(
                    season_nullable=season,
                    season_type_nullable=st,
                    date_from_nullable=nba_date(day),
                    date_to_nullable=nba_date(day),
                    league_id_nullable="00",
                    timeout=NBA_REQUEST_TIMEOUT,
                )
            )
            rows.extend(
                dataset_rows(endpoint.get_normalized_dict(), "PlayerGameLogs", "player_game_logs")
            )
        except Exception:
            continue
    return rows


def _box_score_player_stats(game_id: str) -> list[dict]:
    from nba_api.stats.endpoints import boxscoretraditionalv2

    endpoint = nba_call(
        lambda: boxscoretraditionalv2.BoxScoreTraditionalV2(
            game_id=game_id,
            timeout=NBA_REQUEST_TIMEOUT,
        )
    )
    return dataset_rows(endpoint.get_normalized_dict(), "PlayerStats")


def _map_player_game_log(
    raw: dict,
    *,
    season: str,
    team_abbr_map: dict[str, int],
    scraped_at: datetime,
    known_game_ids: set[str] | None,
) -> dict | None:
    player_id = to_int(row_get(raw, "PLAYER_ID", "Player_ID"))
    game_id = to_str(row_get(raw, "GAME_ID", "Game_ID"))
    matchup = to_str(row_get(raw, "MATCHUP")) or ""
    if player_id is None or not game_id or not matchup:
        return None
    if known_game_ids is not None and game_id not in known_game_ids:
        logger.debug("Skipping log for unknown game_id=%s player_id=%s", game_id, player_id)
        return None

    team_id = to_int(row_get(raw, "TEAM_ID"))
    if team_id is None:
        team_id = resolve_team_id(matchup_team_abbr(matchup), team_abbr_map)
    if team_id is None:
        logger.warning("Could not resolve team_id for player_id=%s matchup=%s", player_id, matchup)
        return None

    game_date_raw = row_get(raw, "GAME_DATE")
    if game_date_raw is None:
        return None

    wl = to_str(row_get(raw, "WL"))
    if wl:
        wl = wl[:1].upper()

    return {
        "player_id": player_id,
        "game_id": game_id,
        "team_id": team_id,
        "game_date": parse_game_date(game_date_raw),
        "season": season,
        "matchup": matchup[:20],
        "wl": wl,
        "min": parse_minutes(row_get(raw, "MIN")),
        "pts": to_int(row_get(raw, "PTS")),
        "reb": to_int(row_get(raw, "REB")),
        "ast": to_int(row_get(raw, "AST")),
        "stl": to_int(row_get(raw, "STL")),
        "blk": to_int(row_get(raw, "BLK")),
        "tov": to_int(row_get(raw, "TOV", "TO")),
        "fgm": to_int(row_get(raw, "FGM")),
        "fga": to_int(row_get(raw, "FGA")),
        "fg_pct": to_float(row_get(raw, "FG_PCT")),
        "fg3m": to_int(row_get(raw, "FG3M")),
        "fg3a": to_int(row_get(raw, "FG3A")),
        "fg3_pct": to_float(row_get(raw, "FG3_PCT")),
        "ftm": to_int(row_get(raw, "FTM")),
        "fta": to_int(row_get(raw, "FTA")),
        "ft_pct": to_float(row_get(raw, "FT_PCT")),
        "plus_minus": to_int(row_get(raw, "PLUS_MINUS")),
        "scraped_at": scraped_at,
    }
