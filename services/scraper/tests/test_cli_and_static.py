from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from main import cli, main
from scrapers import current_season
from scrapers.players import scrape_players, upsert_player_stubs
from scrapers.teams import (
    TEAM_ABBREVIATION_ALIASES,
    resolve_team_id,
    scrape_teams,
    team_id_by_abbreviation,
)


@contextmanager
def _session(mock_session):
    yield mock_session


@pytest.mark.unit
def test_scrape_teams(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "scrapers.teams.static_teams.get_teams",
        lambda: [
            {
                "id": 1610612744,
                "abbreviation": "GSW",
                "full_name": "Golden State Warriors",
                "city": "Golden State",
                "nickname": "Warriors",
            },
            {
                "id": 1,
                "abbreviation": "ZZZ",
                "full_name": "Unknown",
                "city": "X",
                "nickname": "X",
            },
        ],
    )
    session = MagicMock()
    monkeypatch.setattr("scrapers.teams.get_session", lambda: _session(session))
    monkeypatch.setattr("scrapers.teams.upsert_rows", lambda *args, **kwargs: 1)
    assert scrape_teams() == 1


@pytest.mark.unit
def test_team_id_by_abbreviation_from_db() -> None:
    session = MagicMock()
    row = MagicMock(abbreviation="gsw", team_id=1610612744)
    session.query.return_value.all.return_value = [row]
    assert team_id_by_abbreviation(session) == {"GSW": 1610612744}


@pytest.mark.unit
def test_team_id_by_abbreviation_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    session.query.return_value.all.return_value = []
    monkeypatch.setattr(
        "scrapers.teams.static_teams.get_teams",
        lambda: [{"id": 1, "abbreviation": "BOS"}],
    )
    assert team_id_by_abbreviation(session) == {"BOS": 1}


@pytest.mark.unit
def test_team_id_by_abbreviation_historical_aliases() -> None:
    session = MagicMock()
    session.query.return_value.all.return_value = [
        MagicMock(abbreviation="BKN", team_id=1610612751),
        MagicMock(abbreviation="NOP", team_id=1610612740),
        MagicMock(abbreviation="OKC", team_id=1610612760),
        MagicMock(abbreviation="CHA", team_id=1610612766),
        MagicMock(abbreviation="PHX", team_id=1610612756),
        MagicMock(abbreviation="NYK", team_id=1610612752),
    ]
    mapped = team_id_by_abbreviation(session)
    assert mapped["BKN"] == 1610612751
    assert mapped["NJN"] == 1610612751
    assert mapped["BRK"] == 1610612751
    assert mapped["NOP"] == 1610612740
    assert mapped["NOH"] == 1610612740
    assert mapped["NOK"] == 1610612740
    assert mapped["OKC"] == 1610612760
    assert mapped["SEA"] == 1610612760
    assert mapped["CHA"] == 1610612766
    assert mapped["CHO"] == 1610612766
    assert mapped["CHH"] == 1610612766
    assert mapped["PHX"] == 1610612756
    assert mapped["PHO"] == 1610612756
    assert mapped["NYK"] == 1610612752
    assert set(TEAM_ABBREVIATION_ALIASES) <= set(mapped)
    assert resolve_team_id("NJN", {"BKN": 1610612751}) == 1610612751
    assert resolve_team_id("NOH", {"NOP": 1610612740}) == 1610612740
    assert resolve_team_id("ZZZ", mapped) is None
    assert resolve_team_id(None, mapped) is None


@pytest.mark.unit
def test_scrape_players_without_enrich(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "scrapers.players.static_players.get_players",
        lambda: [
            {
                "id": 2544,
                "first_name": "LeBron",
                "last_name": "James",
                "full_name": "LeBron James",
                "is_active": True,
            }
        ],
    )
    monkeypatch.setattr("scrapers.players.get_session", lambda: _session(MagicMock()))
    monkeypatch.setattr("scrapers.players.upsert_rows", lambda *args, **kwargs: 1)
    assert scrape_players(enrich=False) == 1


@pytest.mark.unit
def test_scrape_players_enrich_success_and_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "scrapers.players.static_players.get_players",
        lambda: [
            {"id": 1, "first_name": "A", "last_name": "B", "full_name": "A B", "is_active": False},
            {"id": 2, "first_name": "C", "last_name": "D", "full_name": "C D", "is_active": False},
        ],
    )

    class Endpoint:
        def __init__(self, payload):
            self._payload = payload

        def get_normalized_dict(self):
            return self._payload

    def fake_nba_call(fn):
        return fn()

    monkeypatch.setattr("scrapers.players.nba_call", fake_nba_call)

    def fake_info(player_id, timeout=None):
        if player_id == 1:
            return Endpoint(
                {
                    "CommonPlayerInfo": [
                        {
                            "TEAM_ID": 1610612747,
                            "BIRTHDATE": "1984-12-30T00:00:00",
                            "JERSEY": "23",
                            "POSITION": "F",
                            "HEIGHT": "6-9",
                            "WEIGHT": "250",
                            "FROM_YEAR": 2003,
                            "TO_YEAR": 2025,
                        }
                    ]
                }
            )
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "nba_api.stats.endpoints.commonplayerinfo.CommonPlayerInfo",
        fake_info,
    )
    monkeypatch.setattr("scrapers.players.get_session", lambda: _session(MagicMock()))
    captured = []

    def capture(_session, _model, rows, _conflict):
        captured.extend(rows)
        return len(rows)

    monkeypatch.setattr("scrapers.players.upsert_rows", capture)
    assert scrape_players(enrich=True) == 2
    assert captured[0]["jersey_number"] == "23"
    assert captured[1]["jersey_number"] is None


@pytest.mark.unit
def test_upsert_player_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("scrapers.players.get_session", lambda: _session(MagicMock()))
    monkeypatch.setattr("scrapers.players.upsert_rows", lambda *args, **kwargs: 2)
    assert upsert_player_stubs([]) == 0
    assert (
        upsert_player_stubs(
            [
                {"player_id": 1, "full_name": "Test Player"},
                {"player_id": 2, "first_name": "A", "last_name": "B", "is_active": False},
            ]
        )
        == 2
    )


@pytest.mark.unit
def test_main_invokes_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    called = []
    monkeypatch.setattr("main.cli", lambda: called.append(True))
    main()
    assert called == [True]


@pytest.mark.unit
def test_cli_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("main.scrape_teams", lambda: 30)
    monkeypatch.setattr("main.scrape_players", lambda enrich=False: 10)
    monkeypatch.setattr("main.scrape_contracts", lambda teams=None: (8, 2))
    monkeypatch.setattr("main.scrape_games", lambda season: 82)
    monkeypatch.setattr("main.scrape_player_game_logs", lambda season, active_only=False: 5)
    monkeypatch.setattr("main.scrape_todays_games", lambda: [])
    monkeypatch.setattr("main.scrape_standings", lambda season: 30)
    monkeypatch.setattr("main.scrape_injuries", lambda: 2)
    monkeypatch.setattr("main.scrape_odds", lambda: 0)
    monkeypatch.setattr("main.stamp_cli_success", lambda: None)
    runner = CliRunner()
    assert runner.invoke(cli, ["scrape-teams"]).exit_code == 0
    assert runner.invoke(cli, ["scrape-players"]).exit_code == 0
    assert runner.invoke(cli, ["scrape-games", "--season", "2024-25"]).exit_code == 0
    assert (
        runner.invoke(cli, ["scrape-game-logs", "--season", "2024-25", "--active-only"]).exit_code
        == 0
    )
    daily = runner.invoke(cli, ["scrape-daily"])
    assert daily.exit_code == 0
    assert "No completed games today" in daily.output
    assert "Standings: 30" in daily.output
    assert "Injuries: 2" in daily.output
    assert "Odds: 0" in daily.output
    assert "Player contracts: 8" in daily.output
    result = runner.invoke(cli, ["scrape-all", "--seasons", "2024-25", "--active-only"])
    assert result.exit_code == 0
    assert "Standings 2024-25: 30" in result.output
    assert "Reddit posts" not in result.output
    assert "play-by-play" not in result.output.lower()
    standings = runner.invoke(cli, ["scrape-standings", "--season", "2024-25"])
    assert standings.exit_code == 0
    assert "30" in standings.output


@pytest.mark.unit
def test_scrape_all_stamps_success(monkeypatch: pytest.MonkeyPatch) -> None:
    stamped: list[bool] = []
    monkeypatch.setattr("main.scrape_teams", lambda: 30)
    monkeypatch.setattr("main.scrape_players", lambda enrich=False: 10)
    monkeypatch.setattr("main.scrape_contracts", lambda: (8, 2))
    monkeypatch.setattr("main.scrape_games", lambda season: 82)
    monkeypatch.setattr("main.scrape_player_game_logs", lambda season, active_only=False: 5)
    monkeypatch.setattr("main.scrape_standings", lambda season: 30)
    monkeypatch.setattr("main.stamp_cli_success", lambda: stamped.append(True))
    result = CliRunner().invoke(cli, ["scrape-all", "--seasons", "2024-25", "--active-only"])
    assert result.exit_code == 0
    assert stamped == [True]


@pytest.mark.unit
def test_scrape_all_defaults_to_current_season(monkeypatch: pytest.MonkeyPatch) -> None:
    seasons: list[str] = []
    monkeypatch.setattr("main.scrape_teams", lambda: 30)
    monkeypatch.setattr("main.scrape_players", lambda enrich=False: 10)
    monkeypatch.setattr("main.scrape_contracts", lambda: (8, 2))
    monkeypatch.setattr("main.scrape_games", lambda season: seasons.append(season) or 82)
    monkeypatch.setattr("main.scrape_player_game_logs", lambda season, active_only=False: 5)
    monkeypatch.setattr("main.scrape_standings", lambda season: 30)
    monkeypatch.setattr("main.stamp_cli_success", lambda: None)
    result = CliRunner().invoke(cli, ["scrape-all", "--active-only"])
    assert result.exit_code == 0
    assert seasons == [current_season()]
    assert f"1 season(s): {current_season()}" in result.output


@pytest.mark.unit
def test_scrape_all_failure_does_not_stamp(monkeypatch: pytest.MonkeyPatch) -> None:
    stamped: list[bool] = []
    monkeypatch.setattr(
        "main.scrape_teams",
        lambda: (_ for _ in ()).throw(RuntimeError("teams down")),
    )
    monkeypatch.setattr("main.scrape_players", lambda enrich=False: 10)
    monkeypatch.setattr("main.scrape_contracts", lambda: (8, 2))
    monkeypatch.setattr("main.scrape_games", lambda season: 82)
    monkeypatch.setattr("main.scrape_player_game_logs", lambda season, active_only=False: 5)
    monkeypatch.setattr("main.scrape_standings", lambda season: 30)
    monkeypatch.setattr("main.stamp_cli_success", lambda: stamped.append(True))
    result = CliRunner().invoke(cli, ["scrape-all", "--seasons", "2024-25"])
    assert result.exit_code == 1
    assert stamped == []


@pytest.mark.unit
def test_cli_pipeline_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    config = MagicMock(
        enabled=True,
        season_active=True,
        season_start=None,
        season_end=None,
        scrape_mode="daily",
        target_season=None,
        last_success_at=None,
        last_scrape_date=None,
        reason="ok",
        updated_at=None,
    )
    monkeypatch.setattr("main.get_session", lambda: _session(MagicMock()))
    monkeypatch.setattr("main.load_config", lambda session: config)
    monkeypatch.setattr("main.set_enabled", lambda *args, **kwargs: config)
    monkeypatch.setattr(
        "main.run_pipeline_scrape",
        lambda **kwargs: {
            "run_id": 1,
            "status": "success",
            "action": "daily",
            "detail": "ok",
            "scrape_exit": 0,
        },
    )
    monkeypatch.setattr("main.update_run_dbt_exit", lambda *args, **kwargs: None)
    runner = CliRunner()
    status = runner.invoke(cli, ["pipeline", "status"])
    assert status.exit_code == 0
    assert "season_active=True" in status.output
    assert "scrape_reddit" not in status.output
    assert (
        runner.invoke(
            cli,
            [
                "pipeline",
                "enable",
                "--season-start",
                "2025-10-01",
                "--scrape-mode",
                "daily",
            ],
        ).exit_code
        == 0
    )
    assert runner.invoke(cli, ["pipeline", "enable", "--no-season-active"]).exit_code == 0
    assert runner.invoke(cli, ["pipeline", "disable"]).exit_code == 0
    assert runner.invoke(cli, ["pipeline", "run-once"]).exit_code == 0
    assert (
        runner.invoke(cli, ["pipeline", "mark-dbt", "--run-id", "1", "--dbt-exit", "0"]).exit_code
        == 0
    )


@pytest.mark.unit
def test_cli_pipeline_run_once_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "main.run_pipeline_scrape",
        lambda **kwargs: {
            "run_id": 2,
            "status": "failed",
            "action": "daily",
            "detail": "boom",
            "scrape_exit": 1,
        },
    )
    result = CliRunner().invoke(cli, ["pipeline", "run-once", "--force"])
    assert result.exit_code == 1


@pytest.mark.unit
def test_cli_daily_with_games(monkeypatch: pytest.MonkeyPatch) -> None:
    pbp_ids: list[object] = []
    monkeypatch.setattr("main.scrape_todays_games", lambda: [{"game_id": "002"}])
    monkeypatch.setattr("main.scrape_logs_for_games", lambda games: 12)
    monkeypatch.setattr(
        "main.scrape_play_by_play",
        lambda **kwargs: pbp_ids.append(kwargs.get("game_ids")) or 8,
    )
    monkeypatch.setattr("main.scrape_standings", lambda season: 30)
    monkeypatch.setattr("main.scrape_injuries", lambda: 1)
    monkeypatch.setattr("main.scrape_odds", lambda: 3)
    monkeypatch.setattr("main.scrape_contracts", lambda: (8, 2))
    monkeypatch.setattr("main.stamp_cli_success", lambda: None)
    result = CliRunner().invoke(cli, ["scrape-daily"])
    assert result.exit_code == 0
    assert "12" in result.output
    assert "Standings: 30" in result.output
    assert "Play-by-play: 8" in result.output
    assert "Player contracts: 8" in result.output
    assert pbp_ids == [["002"]]
