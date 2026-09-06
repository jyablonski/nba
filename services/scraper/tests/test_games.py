from contextlib import contextmanager
from datetime import date, datetime
from unittest.mock import MagicMock

import pytest

from scrapers.games import (
    _is_final_status,
    _merge_game_rows,
    _merge_league_schedule,
    _merge_scoreboard,
    _normalize_game_status,
    _schedule_seasons,
    _season_type_from_game_id,
    scrape_games,
    scrape_todays_games,
)


@contextmanager
def _session(mock_session):
    yield mock_session


def _count_session(count: int) -> MagicMock:
    session = MagicMock()
    session.query.return_value.scalar.return_value = count
    return session


def _ids_session(ids: list[int]) -> MagicMock:
    session = MagicMock()
    session.query.return_value.order_by.return_value.all.return_value = [(item,) for item in ids]
    return session


def _abbr_session(pairs: list[tuple[int, str]] | None = None) -> MagicMock:
    session = MagicMock()
    session.query.return_value.all.return_value = pairs or []
    return session


@pytest.mark.unit
def test_season_type_from_game_id() -> None:
    assert _season_type_from_game_id("0022400001") == "Regular Season"
    assert _season_type_from_game_id("0042400001") == "Playoffs"
    assert _season_type_from_game_id("0052400001") == "PlayIn"
    assert _season_type_from_game_id("0012400001") == "Pre Season"
    assert _season_type_from_game_id("xx") == "Regular Season"


@pytest.mark.unit
def test_merge_game_rows() -> None:
    games: dict[str, dict] = {}
    _merge_game_rows(
        games,
        [
            {
                "GAME_ID": "0022400001",
                "MATCHUP": "GSW vs. LAL",
                "TEAM_ID": 1610612744,
                "GAME_DATE": "2024-10-22",
                "PTS": 120,
                "ARENA": "Chase Center",
                "CITY": "San Francisco",
                "STATE": "CA",
            },
            {
                "GAME_ID": "0022400001",
                "MATCHUP": "LAL @ GSW",
                "TEAM_ID": 1610612747,
                "GAME_DATE": "2024-10-22",
                "PTS": 110,
            },
            {"GAME_ID": None, "TEAM_ID": 1},
        ],
        season="2024-25",
        season_type="Regular Season",
        scraped_at=datetime.now(),
    )
    rec = games["0022400001"]
    assert rec["home_team_id"] == 1610612744
    assert rec["away_team_id"] == 1610612747
    assert rec["home_score"] == 120


@pytest.mark.unit
def test_merge_game_rows_repeated_at_matchup() -> None:
    """Both finder rows can carry the same ``DAL @ DET`` string (2025-26 0022500147)."""
    games: dict[str, dict] = {}
    _merge_game_rows(
        games,
        [
            {
                "GAME_ID": "0022500147",
                "MATCHUP": "DAL @ DET",
                "TEAM_ID": 1610612742,
                "TEAM_ABBREVIATION": "DAL",
                "GAME_DATE": "2025-11-01",
                "PTS": 110,
            },
            {
                "GAME_ID": "0022500147",
                "MATCHUP": "DAL @ DET",
                "TEAM_ID": 1610612765,
                "TEAM_ABBREVIATION": "DET",
                "GAME_DATE": "2025-11-01",
                "PTS": 122,
            },
        ],
        season="2025-26",
        season_type="Regular Season",
        scraped_at=datetime.now(),
    )
    rec = games["0022500147"]
    assert rec["home_team_id"] == 1610612765
    assert rec["away_team_id"] == 1610612742
    assert rec["home_score"] == 122
    assert rec["away_score"] == 110


@pytest.mark.unit
def test_merge_game_rows_repeated_at_uses_team_id_map() -> None:
    games: dict[str, dict] = {}
    _merge_game_rows(
        games,
        [
            {
                "GAME_ID": "0022501230",
                "MATCHUP": "SAS @ OKC",
                "TEAM_ID": 1610612760,
                "GAME_DATE": "2025-12-13",
                "PTS": 109,
            },
            {
                "GAME_ID": "0022501230",
                "MATCHUP": "SAS @ OKC",
                "TEAM_ID": 1610612759,
                "GAME_DATE": "2025-12-13",
                "PTS": 111,
            },
        ],
        season="2025-26",
        season_type="Regular Season",
        scraped_at=datetime.now(),
        team_abbreviations={1610612760: "OKC", 1610612759: "SAS"},
    )
    rec = games["0022501230"]
    assert rec["home_team_id"] == 1610612760
    assert rec["away_team_id"] == 1610612759
    assert rec["home_score"] == 109
    assert rec["away_score"] == 111


@pytest.mark.unit
def test_scrape_games(monkeypatch: pytest.MonkeyPatch) -> None:
    sessions = [_count_session(1), _abbr_session(), _ids_session([1610612744]), MagicMock()]
    monkeypatch.setattr("scrapers.games.get_session", lambda: _session(sessions.pop(0)))
    monkeypatch.setattr(
        "scrapers.games._league_game_finder",
        lambda **kwargs: (
            [
                {
                    "GAME_ID": "0022400001",
                    "MATCHUP": "GSW vs. LAL",
                    "TEAM_ID": 1610612744,
                    "GAME_DATE": "2024-10-22",
                    "PTS": 100,
                },
                {
                    "GAME_ID": "0022400001",
                    "MATCHUP": "LAL @ GSW",
                    "TEAM_ID": 1610612747,
                    "GAME_DATE": "2024-10-22",
                    "PTS": 90,
                },
            ]
            if kwargs["season_type"] == "Regular Season"
            else (_ for _ in ()).throw(RuntimeError("skip"))
        ),
    )
    monkeypatch.setattr("scrapers.games.upsert_rows", lambda *args, **kwargs: 1)
    monkeypatch.setattr("scrapers.games._merge_league_schedule", lambda *args, **kwargs: None)
    assert scrape_games("2024-25") == 1


@pytest.mark.unit
def test_scrape_games_merges_per_team_sides(monkeypatch: pytest.MonkeyPatch) -> None:
    sessions = [
        _count_session(2),
        _abbr_session(),
        _ids_session([1610612744, 1610612747]),
        MagicMock(),
    ]
    monkeypatch.setattr("scrapers.games.get_session", lambda: _session(sessions.pop(0)))
    captured: list[list[dict]] = []

    def fake_finder(**kwargs):
        if kwargs["season_type"] != "Regular Season":
            return []
        if kwargs.get("team_id") == 1610612744:
            return [
                {
                    "GAME_ID": "0022500147",
                    "MATCHUP": "DET vs. DAL",
                    "TEAM_ID": 1610612744,
                    "GAME_DATE": "2025-11-01",
                    "PTS": 122,
                }
            ]
        if kwargs.get("team_id") == 1610612747:
            return [
                {
                    "GAME_ID": "0022500147",
                    "MATCHUP": "DAL @ DET",
                    "TEAM_ID": 1610612747,
                    "GAME_DATE": "2025-11-01",
                    "PTS": 110,
                }
            ]
        return []

    def fake_upsert(_session, _model, rows, _conflict):
        captured.append(rows)
        return len(rows)

    monkeypatch.setattr("scrapers.games._league_game_finder", fake_finder)
    monkeypatch.setattr("scrapers.games.upsert_rows", fake_upsert)
    monkeypatch.setattr("scrapers.games._merge_league_schedule", lambda *args, **kwargs: None)
    assert scrape_games("2025-26") == 1
    game = captured[0][0]
    assert game["game_id"] == "0022500147"
    assert game["home_team_id"] == 1610612744
    assert game["away_team_id"] == 1610612747
    assert game["home_score"] == 122
    assert game["away_score"] == 110


@pytest.mark.unit
def test_scrape_todays_games_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("scrapers.games.get_session", lambda: _session(_count_session(1)))
    monkeypatch.setattr(
        "scrapers.games._merge_scoreboard",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("scoreboard down")),
    )
    monkeypatch.setattr("scrapers.games._league_game_finder", lambda **kwargs: [])
    monkeypatch.setattr(
        "scrapers.games._merge_league_schedule",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("schedule down")),
    )
    assert scrape_todays_games(date(2024, 10, 22)) == []


@pytest.mark.unit
def test_is_final_status() -> None:
    assert _is_final_status("Final") is True
    assert _is_final_status("3") is True
    assert _is_final_status("Scheduled") is False
    assert _is_final_status("7:00 pm ET") is False


@pytest.mark.unit
def test_scrape_todays_games_persists_scheduled(monkeypatch: pytest.MonkeyPatch) -> None:
    sessions = [_count_session(1), MagicMock()]
    monkeypatch.setattr("scrapers.games.get_session", lambda: _session(sessions.pop(0)))
    captured: list[list[dict]] = []

    def fake_merge(games, today, *, season, scraped_at):
        games["0022400999"] = {
            "game_id": "0022400999",
            "season": season,
            "season_type": "Regular Season",
            "game_date": today,
            "home_team_id": 1,
            "away_team_id": 2,
            "home_score": None,
            "away_score": None,
            "status": "Scheduled",
            "scraped_at": scraped_at,
        }

    def fake_upsert(_session, _model, rows, _conflict):
        captured.append(rows)
        return len(rows)

    monkeypatch.setattr("scrapers.games._merge_scoreboard", fake_merge)
    monkeypatch.setattr("scrapers.games.upsert_rows", fake_upsert)
    monkeypatch.setattr("scrapers.games._merge_league_schedule", lambda *args, **kwargs: None)
    rows = scrape_todays_games(date(2024, 10, 22), days_ahead=0)
    assert rows == []
    assert len(captured[0]) == 1
    assert captured[0][0]["status"] == "Scheduled"


@pytest.mark.unit
def test_scrape_todays_games_from_scoreboard(monkeypatch: pytest.MonkeyPatch) -> None:
    sessions = [_count_session(1), MagicMock()]
    monkeypatch.setattr("scrapers.games.get_session", lambda: _session(sessions.pop(0)))

    def fake_merge(games, today, *, season, scraped_at):
        games["0022400001"] = {
            "game_id": "0022400001",
            "season": season,
            "season_type": "Regular Season",
            "game_date": today,
            "home_team_id": 1,
            "away_team_id": 2,
            "home_score": 100,
            "away_score": 90,
            "status": "Final",
            "scraped_at": scraped_at,
        }

    monkeypatch.setattr("scrapers.games._merge_scoreboard", fake_merge)
    monkeypatch.setattr("scrapers.games.upsert_rows", lambda *args, **kwargs: 1)
    monkeypatch.setattr("scrapers.games._merge_league_schedule", lambda *args, **kwargs: None)
    rows = scrape_todays_games(date(2024, 10, 22), days_ahead=0)
    assert len(rows) == 1


@pytest.mark.unit
def test_merge_scoreboard(monkeypatch: pytest.MonkeyPatch) -> None:
    class Endpoint:
        def get_normalized_dict(self):
            return {
                "GameHeader": [
                    {
                        "GAME_ID": "0022400100",
                        "HOME_TEAM_ID": 1,
                        "VISITOR_TEAM_ID": 2,
                        "GAME_STATUS_ID": 3,
                        "GAME_STATUS_TEXT": "Final",
                        "SEASON": 2024,
                        "GAME_DATE_EST": "2024-10-22",
                        "ARENA_NAME": "Arena",
                        "ARENA_CITY": "City",
                        "ARENA_STATE": "CA",
                    }
                ],
                "LineScore": [
                    {"GAME_ID": "0022400100", "TEAM_ID": 1, "PTS": 111},
                    {"GAME_ID": "0022400100", "TEAM_ID": 2, "PTS": 100},
                ],
            }

    monkeypatch.setattr("scrapers.games.nba_call", lambda fn: Endpoint())
    games: dict[str, dict] = {}
    _merge_scoreboard(games, date(2024, 10, 22), season="2024-25", scraped_at=datetime.now())
    assert games["0022400100"]["home_score"] == 111
    assert games["0022400100"]["status"] == "Final"


@pytest.mark.unit
def test_merge_scoreboard_scheduled(monkeypatch: pytest.MonkeyPatch) -> None:
    class Endpoint:
        def get_normalized_dict(self):
            return {
                "GameHeader": [
                    {
                        "GAME_ID": "0022400200",
                        "HOME_TEAM_ID": 1,
                        "VISITOR_TEAM_ID": 2,
                        "GAME_STATUS_ID": 1,
                        "GAME_STATUS_TEXT": "7:00 pm ET",
                        "SEASON": 2024,
                        "GAME_DATE_EST": "2024-10-23",
                    }
                ],
                "LineScore": [],
            }

    monkeypatch.setattr("scrapers.games.nba_call", lambda fn: Endpoint())
    games: dict[str, dict] = {}
    _merge_scoreboard(games, date(2024, 10, 23), season="2024-25", scraped_at=datetime.now())
    assert games["0022400200"]["status"] == "Scheduled"
    assert games["0022400200"]["home_score"] is None


@pytest.mark.unit
def test_schedule_seasons_includes_next_before_october() -> None:
    assert _schedule_seasons(date(2026, 9, 5)) == ["2025-26", "2026-27"]
    assert _schedule_seasons(date(2026, 11, 1)) == ["2026-27"]


@pytest.mark.unit
def test_normalize_game_status() -> None:
    assert _normalize_game_status(3, "Final") == "Final"
    assert _normalize_game_status(1, "7:00 pm ET") == "Scheduled"
    assert _normalize_game_status(2, "Q2 4:12") == "Q2 4:12"


@pytest.mark.unit
def test_merge_league_schedule_upcoming_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "scrapers.games._league_schedule",
        lambda season: [
            {
                "gameId": "0022600001",
                "homeTeam_teamId": 1,
                "awayTeam_teamId": 2,
                "gameDateEst": "2026-10-22T00:00:00",
                "gameStatus": 1,
                "gameStatusText": "7:00 pm ET",
                "seasonYear": "2026-27",
                "arenaName": "Chase Center",
                "arenaCity": "San Francisco",
                "arenaState": "CA",
            },
            {
                "gameId": "0022600300",
                "homeTeam_teamId": 3,
                "awayTeam_teamId": 4,
                "gameDateEst": "2026-11-02",
                "gameStatus": 1,
                "seasonYear": "2026-27",
            },
            {
                "gameId": "0022600999",
                "homeTeam_teamId": 1,
                "awayTeam_teamId": 2,
                "gameDateEst": "2026-09-01",
                "gameStatus": 1,
                "seasonYear": "2026-27",
            },
            {
                "gameId": "0012600001",
                "homeTeam_teamId": 1,
                "awayTeam_teamId": 2,
                "gameDateEst": "2026-10-10",
                "gameStatus": 1,
                "seasonYear": "2026-27",
            },
            {
                "gameId": "0022600002",
                "homeTeam_teamId": 1,
                "awayTeam_teamId": 2,
                "gameDateEst": "2026-10-23",
                "gameStatus": 3,
                "gameStatusText": "Final",
                "seasonYear": "2026-27",
                "homeTeam_score": 110,
                "awayTeam_score": 99,
            },
            {"gameId": None, "homeTeam_teamId": 1},
        ],
    )
    games = {
        "0022600001": {
            "game_id": "0022600001",
            "status": "Final",
            "home_score": 100,
            "away_score": 90,
        }
    }
    _merge_league_schedule(
        games, season="2026-27", scraped_at=datetime.now(), from_date=date(2026, 9, 5)
    )
    assert games["0022600001"]["status"] == "Final"
    assert games["0022600300"]["status"] == "Scheduled"
    assert games["0022600300"]["home_score"] is None
    assert "0022600999" not in games
    assert "0012600001" not in games
    assert "0022600002" not in games


@pytest.mark.unit
def test_merge_league_schedule_adds_rest_of_season(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "scrapers.games._league_schedule",
        lambda season: [
            {
                "GAME_ID": "0022600100",
                "HOME_TEAM_ID": 1610612744,
                "AWAY_TEAM_ID": 1610612747,
                "GAME_DATE": "2026-12-01",
                "GAME_STATUS_ID": 1,
                "SEASON": 2026,
                "ARENA_NAME": "Chase Center",
                "ARENA_CITY": "San Francisco",
            }
        ],
    )
    games: dict[str, dict] = {}
    _merge_league_schedule(
        games, season="2026-27", scraped_at=datetime.now(), from_date=date(2026, 9, 5)
    )
    rec = games["0022600100"]
    assert rec["status"] == "Scheduled"
    assert rec["home_score"] is None
    assert rec["away_score"] is None
    assert rec["arena"] == "Chase Center"
    assert rec["season"] == "2026-27"
    assert rec["season_type"] == "Regular Season"


@pytest.mark.unit
def test_scrape_todays_games_merges_season_schedule(monkeypatch: pytest.MonkeyPatch) -> None:
    sessions = [_count_session(1), MagicMock()]
    monkeypatch.setattr("scrapers.games.get_session", lambda: _session(sessions.pop(0)))
    captured: list[list[dict]] = []
    seasons: list[str] = []

    def fake_merge_schedule(games, *, season, scraped_at, from_date=None):
        seasons.append(season)
        games["0022600888"] = {
            "game_id": "0022600888",
            "season": season,
            "season_type": "Regular Season",
            "game_date": date(2026, 12, 1),
            "home_team_id": 1,
            "away_team_id": 2,
            "home_score": None,
            "away_score": None,
            "status": "Scheduled",
            "scraped_at": scraped_at,
        }

    def fake_upsert(_session, _model, rows, _conflict):
        captured.append(rows)
        return len(rows)

    monkeypatch.setattr(
        "scrapers.games._merge_scoreboard",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr("scrapers.games._merge_league_schedule", fake_merge_schedule)
    monkeypatch.setattr("scrapers.games.upsert_rows", fake_upsert)
    rows = scrape_todays_games(date(2026, 9, 5), days_ahead=0)
    assert rows == []
    assert seasons == ["2025-26", "2026-27"]
    assert captured[0][0]["game_id"] == "0022600888"


@pytest.mark.unit
def test_scrape_games_merges_season_schedule(monkeypatch: pytest.MonkeyPatch) -> None:
    sessions = [_count_session(1), _abbr_session(), _ids_session([1]), MagicMock()]
    monkeypatch.setattr("scrapers.games.get_session", lambda: _session(sessions.pop(0)))
    captured: list[list[dict]] = []

    def fake_merge_schedule(games, *, season, scraped_at, from_date=None):
        games["0022400999"] = {
            "game_id": "0022400999",
            "season": season,
            "season_type": "Regular Season",
            "game_date": date(2025, 4, 1),
            "home_team_id": 1,
            "away_team_id": 2,
            "home_score": None,
            "away_score": None,
            "status": "Scheduled",
            "scraped_at": scraped_at,
        }

    def fake_upsert(_session, _model, rows, _conflict):
        captured.append(rows)
        return len(rows)

    monkeypatch.setattr("scrapers.games._league_game_finder", lambda **kwargs: [])
    monkeypatch.setattr("scrapers.games._merge_league_schedule", fake_merge_schedule)
    monkeypatch.setattr("scrapers.games.upsert_rows", fake_upsert)
    assert scrape_games("2024-25") == 1
    assert captured[0][0]["status"] == "Scheduled"


@pytest.mark.unit
def test_scrape_games_schedule_failure_is_nonfatal(monkeypatch: pytest.MonkeyPatch) -> None:
    sessions = [_count_session(1), _abbr_session(), _ids_session([1]), MagicMock()]
    monkeypatch.setattr("scrapers.games.get_session", lambda: _session(sessions.pop(0)))
    monkeypatch.setattr("scrapers.games._league_game_finder", lambda **kwargs: [])
    monkeypatch.setattr(
        "scrapers.games._merge_league_schedule",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("schedule down")),
    )
    monkeypatch.setattr("scrapers.games.upsert_rows", lambda *args, **kwargs: 0)
    assert scrape_games("2024-25") == 0


@pytest.mark.unit
def test_merge_league_schedule_skips_bad_dates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "scrapers.games._league_schedule",
        lambda season: [
            {
                "gameId": "0022600400",
                "homeTeam_teamId": 1,
                "awayTeam_teamId": 2,
                "gameDateEst": "not-a-date",
                "gameStatus": 1,
            }
        ],
    )
    games: dict[str, dict] = {}
    _merge_league_schedule(games, season="2026-27", scraped_at=datetime.now())
    assert games == {}


@pytest.mark.unit
def test_league_schedule_uses_season_games(monkeypatch: pytest.MonkeyPatch) -> None:
    class Endpoint:
        def get_normalized_dict(self):
            return {"SeasonGames": [{"gameId": "0022600001"}]}

    monkeypatch.setattr("scrapers.games.nba_call", lambda fn: Endpoint())
    from scrapers.games import _league_schedule

    assert _league_schedule("2026-27")[0]["gameId"] == "0022600001"
