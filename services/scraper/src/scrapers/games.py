"""Scrape game results into source.games."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from sqlalchemy import func

from db import get_session, upsert_rows
from models import Game, Team
from scrapers import (
    GAME_SEASON_TYPES,
    NBA_REQUEST_TIMEOUT,
    current_season,
    dataset_rows,
    matchup_row_is_home,
    nba_call,
    nba_date,
    parse_game_date,
    row_get,
    season_from_start_year,
    to_int,
    to_str,
)
from scrapers.teams import scrape_teams

logger = logging.getLogger(__name__)


def _ensure_teams() -> None:
    with get_session() as session:
        count = session.query(func.count(Team.team_id)).scalar() or 0
    if count == 0:
        logger.info("No teams in source.teams; scraping teams first")
        scrape_teams()


def _team_ids() -> list[int]:
    with get_session() as session:
        return [team_id for (team_id,) in session.query(Team.team_id).order_by(Team.team_id).all()]


def _team_abbreviations() -> dict[int, str]:
    with get_session() as session:
        return {
            team_id: abbreviation
            for team_id, abbreviation in session.query(Team.team_id, Team.abbreviation).all()
        }


def _finder_scopes(team_ids: list[int]) -> list[int | None]:
    """Per-team LeagueGameFinder so a league-wide dump cannot drop a Final."""
    return list(team_ids) if team_ids else [None]


def scrape_games(season: str) -> int:
    _ensure_teams()
    scraped_at = datetime.now()
    team_abbreviations = _team_abbreviations()
    games: dict[str, dict] = {}
    for team_id in _finder_scopes(_team_ids()):
        for season_type in GAME_SEASON_TYPES:
            try:
                rows = _league_game_finder(season=season, season_type=season_type, team_id=team_id)
            except Exception:
                logger.warning(
                    "LeagueGameFinder failed for %s %s team_id=%s; skipping",
                    season,
                    season_type,
                    team_id,
                )
                continue
            _merge_game_rows(
                games,
                rows,
                season=season,
                season_type=season_type,
                scraped_at=scraped_at,
                team_abbreviations=team_abbreviations,
            )

    try:
        _merge_league_schedule(games, season=season, scraped_at=scraped_at, from_date=date.today())
    except Exception:
        logger.warning("ScheduleLeagueV2 failed for %s; upcoming slate not merged", season)

    records = [
        game for game in games.values() if game.get("home_team_id") and game.get("away_team_id")
    ]
    with get_session() as session:
        written = upsert_rows(session, Game, records, ["game_id"])
    logger.info("Upserted %s games for season %s", written, season)
    return written


def scrape_todays_games(today: date | None = None, *, days_ahead: int = 7) -> list[dict]:
    """Persist today's scoreboard, the next ``days_ahead`` dates, and the rest of the season slate.

    ScoreboardV2 covers the near-term window (live status / scores). ScheduleLeagueV2
    fills remaining current-season games (and the next season before October).
    Scheduled / upcoming rows are stored with nullable scores. Returns only
    completed (Final) game rows so log scraping stays Final-only.
    """
    _ensure_teams()
    today = today or date.today()
    season = current_season(today)
    scraped_at = datetime.now()
    games: dict[str, dict] = {}
    horizon = max(0, int(days_ahead))

    scoreboard_ok = False
    for offset in range(horizon + 1):
        day = today + timedelta(days=offset)
        try:
            _merge_scoreboard(games, day, season=season, scraped_at=scraped_at)
            scoreboard_ok = True
        except Exception:
            logger.warning("ScoreboardV2 failed for %s", day)

    for schedule_season in _schedule_seasons(today):
        try:
            _merge_league_schedule(
                games, season=schedule_season, scraped_at=scraped_at, from_date=today
            )
        except Exception:
            logger.warning("ScheduleLeagueV2 failed for %s", schedule_season)

    if not games and not scoreboard_ok:
        logger.warning("ScoreboardV2 failed for %s; falling back to LeagueGameFinder", today)
        for season_type in GAME_SEASON_TYPES:
            try:
                rows = _league_game_finder(
                    season=season,
                    season_type=season_type,
                    date_from=today,
                    date_to=today,
                )
            except Exception:
                continue
            _merge_game_rows(
                games,
                rows,
                season=season,
                season_type=season_type,
                scraped_at=scraped_at,
                team_abbreviations=_team_abbreviations(),
            )

    records = [
        game for game in games.values() if game.get("home_team_id") and game.get("away_team_id")
    ]
    if not records:
        logger.info("No scoreboard games from %s through +%s days", today, horizon)
        return []

    with get_session() as session:
        upsert_rows(session, Game, records, ["game_id"])
    finals = [game for game in records if _is_final_status(game.get("status"))]
    logger.info(
        "Upserted %s games (%s Final) for %s (Scoreboard +%s days plus season schedule)",
        len(records),
        len(finals),
        today,
        horizon,
    )
    return finals


def _is_final_status(status: object) -> bool:
    return str(status or "").lower() in {"final", "3"}


def _schedule_seasons(today: date) -> list[str]:
    """Seasons to pull from ScheduleLeagueV2.

    October starts a new season. Before October, also pull the upcoming season
    so the off-season slate is ingested.
    """
    current = current_season(today)
    seasons = [current]
    if today.month < 10:
        upcoming = season_from_start_year(today.year)
        if upcoming not in seasons:
            seasons.append(upcoming)
    return seasons


def _normalize_game_status(status_id: int | None, status_text: str) -> str:
    text = status_text or ""
    if status_id == 3 or text.lower().startswith("final"):
        return "Final"
    if status_id == 1:
        return "Scheduled"
    return (text or "Scheduled")[:20]


def _league_game_finder(
    *,
    season: str,
    season_type: str,
    team_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict]:
    from nba_api.stats.endpoints import leaguegamefinder

    kwargs: dict = {
        "player_or_team_abbreviation": "T",
        "season_nullable": season,
        "league_id_nullable": "00",
        "season_type_nullable": season_type,
        "timeout": NBA_REQUEST_TIMEOUT,
    }
    if team_id is not None:
        kwargs["team_id_nullable"] = team_id
    if date_from is not None:
        kwargs["date_from_nullable"] = nba_date(date_from)
    if date_to is not None:
        kwargs["date_to_nullable"] = nba_date(date_to)

    endpoint = nba_call(lambda: leaguegamefinder.LeagueGameFinder(**kwargs))
    return dataset_rows(endpoint.get_normalized_dict(), "LeagueGameFinderResults")


def _league_schedule(season: str) -> list[dict]:
    from nba_api.stats.endpoints import scheduleleaguev2

    endpoint = nba_call(
        lambda: scheduleleaguev2.ScheduleLeagueV2(
            league_id="00",
            season=season,
            timeout=NBA_REQUEST_TIMEOUT,
        )
    )
    return dataset_rows(endpoint.get_normalized_dict(), "SeasonGames", "season_games")


def _merge_league_schedule(
    games: dict[str, dict],
    *,
    season: str,
    scraped_at: datetime,
    from_date: date | None = None,
) -> None:
    """Merge upcoming ScheduleLeagueV2 rows. Does not overwrite Scoreboard / Final keys."""
    for row in _league_schedule(season):
        game_id = to_str(row_get(row, "gameId", "GAME_ID"))
        home_id = to_int(row_get(row, "homeTeam_teamId", "HOME_TEAM_ID"))
        away_id = to_int(row_get(row, "awayTeam_teamId", "AWAY_TEAM_ID", "VISITOR_TEAM_ID"))
        if not game_id or home_id is None or away_id is None:
            continue
        if _season_type_from_game_id(game_id) == "Pre Season":
            continue
        game_date_raw = row_get(row, "gameDateEst", "gameDate", "GAME_DATE_EST", "GAME_DATE")
        try:
            game_date = parse_game_date(str(game_date_raw)[:10])
        except TypeError, ValueError:
            continue
        if from_date is not None and game_date < from_date:
            continue
        status_id = to_int(row_get(row, "gameStatus", "GAME_STATUS_ID"))
        status_text = to_str(row_get(row, "gameStatusText", "GAME_STATUS_TEXT")) or ""
        status = _normalize_game_status(status_id, status_text)
        if _is_final_status(status):
            continue
        season_year = to_str(row_get(row, "seasonYear", "SEASON"))
        if season_year and "-" in season_year:
            game_season = season_year
        else:
            year = to_int(season_year)
            game_season = season_from_start_year(year) if year is not None else season
        games.setdefault(
            game_id,
            {
                "game_id": game_id,
                "season": game_season,
                "season_type": _season_type_from_game_id(game_id),
                "game_date": game_date,
                "home_team_id": home_id,
                "away_team_id": away_id,
                "home_score": None,
                "away_score": None,
                "arena": to_str(row_get(row, "arenaName", "ARENA_NAME", "ARENA")),
                "city": to_str(row_get(row, "arenaCity", "ARENA_CITY", "CITY")),
                "state": to_str(row_get(row, "arenaState", "ARENA_STATE", "STATE")),
                "status": status[:20],
                "scraped_at": scraped_at,
            },
        )


def _merge_game_rows(
    games: dict[str, dict],
    rows: list[dict],
    *,
    season: str,
    season_type: str,
    scraped_at: datetime,
    team_abbreviations: dict[int, str] | None = None,
) -> None:
    abbreviations = team_abbreviations or {}
    for row in rows:
        game_id = to_str(row_get(row, "GAME_ID"))
        matchup = to_str(row_get(row, "MATCHUP")) or ""
        team_id = to_int(row_get(row, "TEAM_ID"))
        if not game_id or team_id is None:
            continue
        rec = games.setdefault(
            game_id,
            {
                "game_id": game_id,
                "season": season,
                "season_type": season_type,
                "game_date": parse_game_date(row_get(row, "GAME_DATE")),
                "home_team_id": None,
                "away_team_id": None,
                "home_score": None,
                "away_score": None,
                "arena": to_str(row_get(row, "ARENA", "ARENA_NAME")),
                "city": to_str(row_get(row, "ARENA_CITY", "CITY")),
                "state": to_str(row_get(row, "ARENA_STATE", "STATE")),
                "status": "Final",
                "scraped_at": scraped_at,
            },
        )
        pts = to_int(row_get(row, "PTS"))
        team_abbr = to_str(row_get(row, "TEAM_ABBREVIATION", "TEAM_ABBREV")) or abbreviations.get(
            team_id
        )
        if matchup_row_is_home(matchup, team_abbr):
            rec["home_team_id"] = team_id
            rec["home_score"] = pts
        else:
            rec["away_team_id"] = team_id
            rec["away_score"] = pts


def _merge_scoreboard(
    games: dict[str, dict], today: date, *, season: str, scraped_at: datetime
) -> None:
    from nba_api.stats.endpoints import scoreboardv2

    endpoint = nba_call(
        lambda: scoreboardv2.ScoreboardV2(
            game_date=today.strftime("%Y-%m-%d"),
            timeout=NBA_REQUEST_TIMEOUT,
        )
    )
    payload = endpoint.get_normalized_dict()
    headers = dataset_rows(payload, "GameHeader")
    lines = dataset_rows(payload, "LineScore")
    scores: dict[tuple[str, int], int | None] = {}
    for line in lines:
        game_id = to_str(row_get(line, "GAME_ID"))
        team_id = to_int(row_get(line, "TEAM_ID"))
        if game_id and team_id is not None:
            scores[(game_id, team_id)] = to_int(row_get(line, "PTS"))

    for header in headers:
        game_id = to_str(row_get(header, "GAME_ID"))
        home_id = to_int(row_get(header, "HOME_TEAM_ID"))
        away_id = to_int(row_get(header, "VISITOR_TEAM_ID", "AWAY_TEAM_ID"))
        if not game_id or home_id is None or away_id is None:
            continue
        status_id = to_int(row_get(header, "GAME_STATUS_ID"))
        status_text = to_str(row_get(header, "GAME_STATUS_TEXT")) or ""
        status = _normalize_game_status(status_id, status_text)
        season_year = to_int(row_get(header, "SEASON"))
        game_season = season_from_start_year(season_year) if season_year is not None else season
        game_date_raw = row_get(header, "GAME_DATE_EST", "GAME_DATE") or today
        games[game_id] = {
            "game_id": game_id,
            "season": game_season,
            "season_type": _season_type_from_game_id(game_id),
            "game_date": parse_game_date(str(game_date_raw)[:10]),
            "home_team_id": home_id,
            "away_team_id": away_id,
            "home_score": scores.get((game_id, home_id)),
            "away_score": scores.get((game_id, away_id)),
            "arena": to_str(row_get(header, "ARENA_NAME", "ARENA")),
            "city": to_str(row_get(header, "ARENA_CITY", "CITY")),
            "state": to_str(row_get(header, "ARENA_STATE", "STATE")),
            "status": status,
            "scraped_at": scraped_at,
        }


def _season_type_from_game_id(game_id: str) -> str:
    """NBA game_id prefix: 001 preseason, 002 regular, 004 playoffs, 005 play-in."""
    if len(game_id) >= 3:
        prefix = game_id[2]
        mapping = {"1": "Pre Season", "2": "Regular Season", "4": "Playoffs", "5": "PlayIn"}
        return mapping.get(prefix, "Regular Season")
    return "Regular Season"
