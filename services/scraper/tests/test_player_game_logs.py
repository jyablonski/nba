from contextlib import contextmanager
from datetime import date, datetime
from unittest.mock import MagicMock

import pytest

from scrapers.player_game_logs import (
    _map_player_game_log,
    scrape_logs_for_games,
    scrape_player_game_logs,
)


@contextmanager
def _session(mock_session):
    yield mock_session


@pytest.mark.unit
def test_map_player_game_log() -> None:
    mapped = _map_player_game_log(
        {
            "PLAYER_ID": 202695,
            "GAME_ID": "0022400001",
            "MATCHUP": "LAC vs. GSW",
            "TEAM_ID": 1610612746,
            "GAME_DATE": "2024-10-22",
            "WL": "W",
            "MIN": "36:00",
            "PTS": 28,
            "REB": 7,
            "AST": 5,
            "STL": 2,
            "BLK": 1,
            "TOV": 3,
            "FGM": 10,
            "FGA": 20,
            "FG_PCT": 0.5,
            "FG3M": 2,
            "FG3A": 6,
            "FG3_PCT": 0.333,
            "FTM": 6,
            "FTA": 6,
            "FT_PCT": 1.0,
            "PLUS_MINUS": 8,
        },
        season="2024-25",
        team_abbr_map={},
        scraped_at=datetime.now(),
        known_game_ids={"0022400001"},
    )
    assert mapped is not None
    assert mapped["pts"] == 28
    assert mapped["wl"] == "W"


CURRENT_TEAM_ABBR_MAP = {
    "BKN": 1610612751,
    "NOP": 1610612740,
    "NYK": 1610612752,
    "CHA": 1610612766,
    "PHX": 1610612756,
    "MEM": 1610612763,
    "GSW": 1610612744,
}


@pytest.mark.unit
def test_map_player_game_log_team_from_matchup() -> None:
    mapped = _map_player_game_log(
        {
            "PLAYER_ID": 1,
            "GAME_ID": "002",
            "MATCHUP": "GSW @ CHI",
            "GAME_DATE": "2024-10-22",
        },
        season="2024-25",
        team_abbr_map={"GSW": 1610612744},
        scraped_at=datetime.now(),
        known_game_ids=None,
    )
    assert mapped["team_id"] == 1610612744


@pytest.mark.unit
@pytest.mark.parametrize(
    ("matchup", "team_id"),
    [
        ("NJN @ CHA", 1610612751),
        ("NOH vs. MEM", 1610612740),
        ("BKN vs. NYK", 1610612751),
        ("BRK vs. NYK", 1610612751),
        ("CHO vs. MEM", 1610612766),
        ("PHO vs. NYK", 1610612756),
    ],
)
def test_map_player_game_log_historical_and_bref_abbrevs(matchup: str, team_id: int) -> None:
    mapped = _map_player_game_log(
        {
            "PLAYER_ID": 1,
            "GAME_ID": "002",
            "MATCHUP": matchup,
            "GAME_DATE": "2010-11-05",
        },
        season="2010-11",
        team_abbr_map=CURRENT_TEAM_ABBR_MAP,
        scraped_at=datetime.now(),
        known_game_ids=None,
    )
    assert mapped is not None
    assert mapped["team_id"] == team_id


@pytest.mark.unit
def test_map_player_game_log_skips() -> None:
    assert (
        _map_player_game_log(
            {"PLAYER_ID": 1},
            season="2024-25",
            team_abbr_map={},
            scraped_at=datetime.now(),
            known_game_ids=None,
        )
        is None
    )
    assert (
        _map_player_game_log(
            {"PLAYER_ID": 1, "GAME_ID": "x", "MATCHUP": "GSW vs. LAL", "GAME_DATE": "2024-10-22"},
            season="2024-25",
            team_abbr_map={},
            scraped_at=datetime.now(),
            known_game_ids={"other"},
        )
        is None
    )
    assert (
        _map_player_game_log(
            {"PLAYER_ID": 1, "GAME_ID": "x", "MATCHUP": "ZZZ vs. LAL", "GAME_DATE": "2024-10-22"},
            season="2024-25",
            team_abbr_map={},
            scraped_at=datetime.now(),
            known_game_ids=None,
        )
        is None
    )
    assert (
        _map_player_game_log(
            {"PLAYER_ID": 1, "GAME_ID": "x", "MATCHUP": "GSW vs. LAL", "TEAM_ID": 1},
            season="2024-25",
            team_abbr_map={},
            scraped_at=datetime.now(),
            known_game_ids=None,
        )
        is None
    )


@pytest.mark.unit
def test_scrape_player_game_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("scrapers.player_game_logs._ensure_reference_data", lambda season: None)
    monkeypatch.setattr(
        "scrapers.player_game_logs._player_ids_for_season", lambda season, active_only=False: [1]
    )
    monkeypatch.setattr(
        "scrapers.player_game_logs._game_ids_for_season", lambda season: {"0022400001"}
    )
    monkeypatch.setattr(
        "scrapers.player_game_logs.team_id_by_abbreviation", lambda session: {"LAC": 1}
    )
    monkeypatch.setattr("scrapers.player_game_logs.get_session", lambda: _session(MagicMock()))
    monkeypatch.setattr(
        "scrapers.player_game_logs._player_game_log",
        lambda player_id, season, season_type: (
            [
                {
                    "PLAYER_ID": 1,
                    "GAME_ID": "0022400001",
                    "MATCHUP": "LAC vs. GSW",
                    "TEAM_ID": 1,
                    "GAME_DATE": "2024-10-22",
                    "PTS": 10,
                }
            ]
            if season_type == "Regular Season"
            else (_ for _ in ()).throw(RuntimeError("skip"))
        ),
    )
    monkeypatch.setattr("scrapers.player_game_logs.upsert_rows", lambda *args, **kwargs: 1)
    assert scrape_player_game_logs("2024-25") == 1


@pytest.mark.unit
def test_scrape_logs_for_games_empty() -> None:
    assert scrape_logs_for_games([]) == 0


@pytest.mark.unit
def test_scrape_logs_for_games(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("scrapers.player_game_logs._ensure_teams", lambda: None)
    monkeypatch.setattr(
        "scrapers.player_game_logs._player_game_logs_for_date",
        lambda season, day: [
            {
                "PLAYER_ID": 1,
                "GAME_ID": "0022400001",
                "PLAYER_NAME": "Test",
                "MATCHUP": "LAC vs. GSW",
                "TEAM_ID": 1,
                "GAME_DATE": "2024-10-22",
                "PTS": 8,
            },
            {"PLAYER_ID": None, "GAME_ID": "0022400001"},
            {"PLAYER_ID": 2, "GAME_ID": "other"},
        ],
    )
    monkeypatch.setattr("scrapers.player_game_logs.team_id_by_abbreviation", lambda session: {})
    monkeypatch.setattr("scrapers.player_game_logs.get_session", lambda: _session(MagicMock()))
    monkeypatch.setattr("scrapers.player_game_logs.upsert_player_stubs", lambda stubs: len(stubs))
    monkeypatch.setattr("scrapers.player_game_logs.upsert_rows", lambda *args, **kwargs: 1)
    written = scrape_logs_for_games(
        [{"game_id": "0022400001", "season": "2024-25"}],
        today=date(2024, 10, 22),
    )
    assert written == 1


@pytest.mark.unit
def test_scrape_logs_for_games_boxscore_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("scrapers.player_game_logs._ensure_teams", lambda: None)
    monkeypatch.setattr(
        "scrapers.player_game_logs._player_game_logs_for_date",
        lambda season, day: (_ for _ in ()).throw(RuntimeError("nope")),
    )
    monkeypatch.setattr("scrapers.player_game_logs._box_score_player_stats", lambda game_id: [])
    monkeypatch.setattr("scrapers.player_game_logs.team_id_by_abbreviation", lambda session: {})
    monkeypatch.setattr("scrapers.player_game_logs.get_session", lambda: _session(MagicMock()))
    assert (
        scrape_logs_for_games([{"game_id": "002", "season": "2024-25"}], today=date(2024, 10, 22))
        == 0
    )


@pytest.mark.unit
def test_scrape_logs_boxscore_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("scrapers.player_game_logs._ensure_teams", lambda: None)
    monkeypatch.setattr(
        "scrapers.player_game_logs._player_game_logs_for_date",
        lambda season, day: (_ for _ in ()).throw(RuntimeError("nope")),
    )
    monkeypatch.setattr(
        "scrapers.player_game_logs._box_score_player_stats",
        lambda game_id: (_ for _ in ()).throw(RuntimeError("box fail")),
    )
    monkeypatch.setattr("scrapers.player_game_logs.team_id_by_abbreviation", lambda session: {})
    monkeypatch.setattr("scrapers.player_game_logs.get_session", lambda: _session(MagicMock()))
    assert scrape_logs_for_games([{"game_id": "002", "season": "2024-25"}]) == 0


@pytest.mark.unit
def test_scrape_player_game_logs_static_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"ids": 0}

    def player_ids(season, active_only=False):
        calls["ids"] += 1
        return [] if calls["ids"] == 1 else [9]

    monkeypatch.setattr("scrapers.player_game_logs._ensure_reference_data", lambda season: None)
    monkeypatch.setattr("scrapers.player_game_logs._player_ids_for_season", player_ids)
    monkeypatch.setattr(
        "scrapers.player_game_logs._static_player_ids", lambda active_only=False: [9]
    )
    monkeypatch.setattr("scrapers.player_game_logs.upsert_player_stubs", lambda stubs: len(stubs))
    monkeypatch.setattr(
        "scrapers.player_game_logs._game_ids_for_season", lambda season: {"0022400001"}
    )
    monkeypatch.setattr("scrapers.player_game_logs.team_id_by_abbreviation", lambda session: {})
    monkeypatch.setattr("scrapers.player_game_logs.get_session", lambda: _session(MagicMock()))
    monkeypatch.setattr("scrapers.player_game_logs._player_game_log", lambda *args, **kwargs: [])
    assert scrape_player_game_logs("2024-25") == 0


@pytest.mark.unit
def test_ensure_teams_and_reference_data(monkeypatch: pytest.MonkeyPatch) -> None:
    from scrapers.player_game_logs import (
        _box_score_player_stats,
        _ensure_reference_data,
        _ensure_teams,
        _game_ids_for_season,
        _player_game_log,
        _player_game_logs_for_date,
        _player_ids_for_season,
        _static_player_ids,
    )

    empty = MagicMock()
    empty.query.return_value.scalar.return_value = 0
    empty.query.return_value.filter.return_value.scalar.return_value = 0
    empty.query.return_value.filter.return_value.all.return_value = []
    monkeypatch.setattr("scrapers.player_game_logs.get_session", lambda: _session(empty))
    scraped = {"teams": 0, "players": 0, "games": 0}

    monkeypatch.setattr(
        "scrapers.player_game_logs.scrape_teams", lambda: scraped.__setitem__("teams", 1)
    )
    monkeypatch.setattr(
        "scrapers.player_game_logs.scrape_players",
        lambda enrich=False: scraped.__setitem__("players", 1),
    )
    monkeypatch.setattr(
        "scrapers.games.scrape_games", lambda season: scraped.__setitem__("games", 1)
    )
    _ensure_teams()
    _ensure_reference_data("2024-25")
    assert scraped == {"teams": 1, "players": 1, "games": 1}

    class StaticPlayers:
        @staticmethod
        def get_active_players():
            return [
                {
                    "id": 1,
                    "first_name": "A",
                    "last_name": "B",
                    "full_name": "A B",
                }
            ]

        @staticmethod
        def get_players():
            return [{"id": 2}]

    import nba_api.stats.static.players as static_players

    monkeypatch.setattr(static_players, "get_active_players", StaticPlayers.get_active_players)
    monkeypatch.setattr(static_players, "get_players", StaticPlayers.get_players)
    monkeypatch.setattr("scrapers.player_game_logs.upsert_player_stubs", lambda stubs: len(stubs))
    assert _static_player_ids(active_only=True) == [1]
    assert _static_player_ids(active_only=False) == [2]
    assert _player_ids_for_season("2024-25", active_only=True) == [1]

    populated = MagicMock()
    populated.query.return_value.filter.return_value.all.return_value = [("002",)]
    monkeypatch.setattr("scrapers.player_game_logs.get_session", lambda: _session(populated))
    assert _game_ids_for_season("2024-25") == {"002"}

    class Endpoint:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def get_normalized_dict(self):
            return {"PlayerGameLog": [{"PLAYER_ID": 1}], "PlayerGameLogs": [], "PlayerStats": []}

    monkeypatch.setattr("scrapers.player_game_logs.nba_call", lambda fn: fn())
    import nba_api.stats.endpoints.boxscoretraditionalv2 as boxscore
    import nba_api.stats.endpoints.playergamelog as playergamelog
    import nba_api.stats.endpoints.playergamelogs as playergamelogs

    monkeypatch.setattr(playergamelog, "PlayerGameLog", Endpoint)
    monkeypatch.setattr(playergamelogs, "PlayerGameLogs", Endpoint)
    monkeypatch.setattr(boxscore, "BoxScoreTraditionalV2", Endpoint)
    assert _player_game_log(1, "2024-25", "Regular Season")[0]["PLAYER_ID"] == 1
    assert _player_game_logs_for_date("2024-25", date(2024, 10, 22)) == []
    assert _box_score_player_stats("002") == []

    monkeypatch.setattr(
        "scrapers.player_game_logs.nba_call",
        lambda fn: (_ for _ in ()).throw(RuntimeError("fail")),
    )
    assert _player_game_logs_for_date("2024-25", date(2024, 10, 22)) == []
