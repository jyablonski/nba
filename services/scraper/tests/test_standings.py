from contextlib import contextmanager
from datetime import date, datetime
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from main import cli
from scrapers.standings import _parse_games_back, _row_to_standing, scrape_standings


@contextmanager
def _session(mock_session):
    yield mock_session


GSW = 1610612744
LAC = 1610612746
KNOWN = {GSW, LAC}


def _standing_session() -> MagicMock:
    session = MagicMock()
    session.query.return_value.scalar.return_value = 2
    session.query.return_value.all.return_value = [(GSW,), (LAC,)]
    return session


@pytest.mark.unit
def test_parse_games_back_dash_and_empty() -> None:
    assert _parse_games_back("-") == 0.0
    assert _parse_games_back(" - ") == 0.0
    assert _parse_games_back("") == 0.0
    assert _parse_games_back("   ") == 0.0
    assert _parse_games_back(None) is None
    assert _parse_games_back("1.5") == 1.5
    assert _parse_games_back(0) == 0.0


@pytest.mark.unit
def test_row_to_standing_maps_v3_headers() -> None:
    rec = _row_to_standing(
        {
            "TeamID": GSW,
            "Conference": "West",
            "Division": "Pacific",
            "PlayoffRank": 1,
            "DivisionRank": 1,
            "WINS": 10,
            "LOSSES": 0,
            "WinPCT": 1.0,
            "GB": "-",
            "ConferenceGamesBack": 0,
            "strCurrentStreak": "W 10",
            "L10": "10-0",
        },
        season="2024-25",
        as_of=date(2024, 12, 1),
        scraped_at=datetime(2024, 12, 1, 12, 0),
        known_team_ids=KNOWN,
    )
    assert rec is not None
    assert rec["team_id"] == GSW
    assert rec["season"] == "2024-25"
    assert rec["season_type"] == "Regular Season"
    assert rec["as_of_date"] == date(2024, 12, 1)
    assert rec["conference"] == "West"
    assert rec["conference_rank"] == 1
    assert rec["games_back"] == 0.0
    assert rec["conf_games_back"] == 0.0
    assert rec["streak"] == "W 10"
    assert rec["last_10"] == "10-0"


@pytest.mark.unit
def test_row_to_standing_fallback_headers() -> None:
    rec = _row_to_standing(
        {
            "TeamID": LAC,
            "Conference": "West",
            "Division": "Pacific",
            "ConferenceRank": 2,
            "DivisionRank": 2,
            "WINS": 8,
            "LOSSES": 2,
            "WinPCT": 0.8,
            "ConferenceGamesBack": 1.5,
            "CurrentStreak": -1,
            "LTen": "7-3",
        },
        season="2024-25",
        as_of=date(2024, 12, 1),
        scraped_at=datetime(2024, 12, 1, 12, 0),
        known_team_ids=KNOWN,
    )
    assert rec is not None
    assert rec["conference_rank"] == 2
    assert rec["games_back"] == 1.5
    assert rec["conf_games_back"] == 1.5
    assert rec["streak"] == "-1"
    assert rec["last_10"] == "7-3"


@pytest.mark.unit
def test_row_to_standing_skips_unknown_and_missing_team() -> None:
    kwargs = dict(
        season="2024-25",
        as_of=date(2024, 12, 1),
        scraped_at=datetime(2024, 12, 1, 12, 0),
        known_team_ids=KNOWN,
    )
    assert _row_to_standing({"TeamID": None, "GB": "0"}, **kwargs) is None
    assert _row_to_standing({"GB": "-"}, **kwargs) is None
    assert _row_to_standing({"TeamID": 999, "GB": "2.0"}, **kwargs) is None


@pytest.mark.unit
def test_scrape_standings(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _standing_session()
    monkeypatch.setattr("scrapers.standings.get_session", lambda: _session(session))
    monkeypatch.setattr(
        "scrapers.standings._league_standings",
        lambda season: [
            {
                "TeamID": GSW,
                "Conference": "West",
                "Division": "Pacific",
                "PlayoffRank": 1,
                "DivisionRank": 1,
                "WINS": 5,
                "LOSSES": 0,
                "WinPCT": 1.0,
                "GB": "-",
                "ConferenceGamesBack": "-",
                "strCurrentStreak": "W 5",
                "L10": "5-0",
            },
            {
                "TeamID": LAC,
                "Conference": "West",
                "PlayoffRank": 2,
                "WINS": 3,
                "LOSSES": 2,
                "WinPCT": 0.6,
                "GB": "1.5",
                "ConferenceGamesBack": "1.5",
                "strCurrentStreak": "L 1",
                "L10": "3-2",
            },
            {"TeamID": None},
            {"TeamID": 999, "GB": "4.0"},
        ],
    )
    captured: list[dict] = []

    def capture(_session, model, rows, conflict):
        assert model.__name__ == "Standing"
        assert conflict == ["season", "season_type", "team_id"]
        captured.extend(rows)
        return len(rows)

    monkeypatch.setattr("scrapers.standings.upsert_rows", capture)
    written = scrape_standings("2024-25", as_of=date(2024, 12, 15))
    assert written == 2
    assert captured[0]["games_back"] == 0.0
    assert captured[0]["as_of_date"] == date(2024, 12, 15)
    assert captured[1]["games_back"] == 1.5
    assert all(row["season_type"] == "Regular Season" for row in captured)


@pytest.mark.unit
def test_scrape_standings_defaults_as_of_today(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _standing_session()
    monkeypatch.setattr("scrapers.standings.get_session", lambda: _session(session))
    monkeypatch.setattr(
        "scrapers.standings._league_standings",
        lambda season: [
            {
                "TeamID": GSW,
                "PlayoffRank": 1,
                "WINS": 1,
                "LOSSES": 0,
                "GB": "",
            }
        ],
    )
    captured: list[dict] = []
    monkeypatch.setattr(
        "scrapers.standings.upsert_rows",
        lambda _s, _m, rows, _c: captured.extend(rows) or len(rows),
    )
    scrape_standings("2024-25")
    assert captured[0]["as_of_date"] == date.today()
    assert captured[0]["games_back"] == 0.0


@pytest.mark.unit
def test_scrape_standings_ensures_teams(monkeypatch: pytest.MonkeyPatch) -> None:
    empty = MagicMock()
    empty.query.return_value.scalar.return_value = 0
    filled = _standing_session()
    sessions = [empty, filled, filled]
    monkeypatch.setattr("scrapers.standings.get_session", lambda: _session(sessions.pop(0)))
    called = {"teams": False}
    monkeypatch.setattr(
        "scrapers.standings.scrape_teams", lambda: called.__setitem__("teams", True)
    )
    monkeypatch.setattr("scrapers.standings._league_standings", lambda season: [])
    monkeypatch.setattr("scrapers.standings.upsert_rows", lambda *args, **kwargs: 0)
    assert scrape_standings("2024-25") == 0
    assert called["teams"] is True


@pytest.mark.unit
def test_league_standings_uses_v3(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    class Endpoint:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def get_normalized_dict(self):
            return {"Standings": [{"TeamID": GSW, "GB": "-"}]}

    monkeypatch.setattr("scrapers.standings.nba_call", lambda fn: fn())

    import nba_api.stats.endpoints.leaguestandingsv3 as leaguestandingsv3

    monkeypatch.setattr(leaguestandingsv3, "LeagueStandingsV3", Endpoint)
    from scrapers.standings import _league_standings

    rows = _league_standings("2024-25")
    assert rows[0]["TeamID"] == GSW
    assert captured["season"] == "2024-25"
    assert captured["season_type"] == "Regular Season"
    assert captured["league_id"] == "00"


@pytest.mark.unit
def test_cli_scrape_standings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("main.scrape_standings", lambda season: 30)
    result = CliRunner().invoke(cli, ["scrape-standings", "--season", "2024-25"])
    assert result.exit_code == 0
    assert "30" in result.output
    assert "2024-25" in result.output
