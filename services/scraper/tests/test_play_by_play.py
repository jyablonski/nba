from contextlib import contextmanager
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from main import cli
from models import PlayByPlay
from scrapers.play_by_play import (
    NoFinalGamesError,
    _actions_from_v3_payload,
    _final_games_for_season,
    _play_by_play_actions,
    map_play_by_play_action,
    scrape_play_by_play,
)


@contextmanager
def _session(mock_session):
    yield mock_session


def _v3_action(**overrides: object) -> dict:
    row = {
        "gameId": "0022400001",
        "actionNumber": 4,
        "actionId": 400,
        "clock": "PT11M32.00S",
        "period": 1,
        "teamId": 1610612744,
        "personId": 201939,
        "scoreHome": "2",
        "scoreAway": "0",
        "actionType": "2pt",
        "subType": "Jump Shot",
        "description": "Curry 18' Jump Shot (2 PTS)",
        "shotResult": "Made",
        "shotDistance": 18,
        "teamTricode": "GSW",
        "playerName": "Stephen Curry",
    }
    row.update(overrides)
    return row


@pytest.mark.unit
def test_map_play_by_play_action() -> None:
    scraped_at = datetime.now()
    mapped = map_play_by_play_action(
        _v3_action(),
        game_id="0022400001",
        season="2025-26",
        scraped_at=scraped_at,
    )
    assert mapped is not None
    assert mapped["game_id"] == "0022400001"
    assert mapped["season"] == "2025-26"
    assert mapped["action_number"] == 4
    assert mapped["action_id"] == 400
    assert mapped["period"] == 1
    assert mapped["clock"] == "PT11M32.00S"
    assert mapped["score_home"] == 2
    assert mapped["score_away"] == 0
    assert mapped["team_id"] == 1610612744
    assert mapped["player_id"] == 201939
    assert mapped["action_type"] == "2pt"
    assert mapped["sub_type"] == "Jump Shot"
    assert mapped["description"] == "Curry 18' Jump Shot (2 PTS)"
    assert mapped["extras"]["shotResult"] == "Made"
    assert mapped["extras"]["shotDistance"] == 18
    assert mapped["extras"]["teamTricode"] == "GSW"
    assert "actionNumber" not in mapped["extras"]
    assert mapped["scraped_at"] == scraped_at


@pytest.mark.unit
def test_map_play_by_play_action_skips_and_nulls() -> None:
    scraped_at = datetime.now()
    assert (
        map_play_by_play_action(
            {"gameId": "002"},
            game_id="002",
            season="2025-26",
            scraped_at=scraped_at,
        )
        is None
    )
    mapped = map_play_by_play_action(
        _v3_action(
            gameId="",
            teamId=0,
            personId=0,
            shotResult="",
            playerName=None,
            clock="PT12M00.00S",
        ),
        game_id="0022400001",
        season="2025-26",
        scraped_at=scraped_at,
    )
    assert mapped is not None
    assert mapped["game_id"] == "0022400001"
    assert mapped["team_id"] is None
    assert mapped["player_id"] is None
    assert mapped["extras"] is None or "shotResult" not in mapped["extras"]
    assert mapped["extras"] is None or "playerName" not in mapped["extras"]


@pytest.mark.unit
def test_map_play_by_play_action_eventnum_alias() -> None:
    mapped = map_play_by_play_action(
        {"EVENTNUM": 9, "ACTION_TYPE": "rebound", "TEAM_ID": 1},
        game_id="002",
        season="2024-25",
        scraped_at=datetime.now(),
    )
    assert mapped is not None
    assert mapped["action_number"] == 9
    assert mapped["action_id"] == 9
    assert mapped["action_type"] == "rebound"
    assert mapped["team_id"] == 1
    assert (
        map_play_by_play_action(
            {"actionNumber": 1, "gameId": ""},
            game_id="",
            season="2025-26",
            scraped_at=datetime.now(),
        )
        is None
    )


@pytest.mark.unit
def test_final_games_for_season(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
        ("0022400001", "2025-26", "Final"),
        ("0022400002", "2025-26", "Scheduled"),
        ("0022400003", "2025-26", "3"),
    ]
    monkeypatch.setattr("scrapers.play_by_play.get_session", lambda: _session(session))
    games = _final_games_for_season("2025-26")
    assert [game["game_id"] for game in games] == ["0022400001", "0022400003"]


@pytest.mark.unit
def test_scrape_play_by_play_raises_without_finals(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("scrapers.play_by_play._final_games_for_season", lambda season: [])
    with pytest.raises(NoFinalGamesError, match="2025-26"):
        scrape_play_by_play("2025-26")


@pytest.mark.unit
def test_scrape_play_by_play_upserts_and_skips_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "scrapers.play_by_play._final_games_for_season",
        lambda season: [
            {"game_id": "0022400001", "season": season},
            {"game_id": "0022400002", "season": season},
            {"game_id": "0022400003", "season": season},
        ],
    )

    def fetch(game_id: str) -> list[dict]:
        if game_id == "0022400002":
            raise RuntimeError("timeout")
        if game_id == "0022400003":
            return [{"gameId": game_id}]
        return [_v3_action(gameId=game_id), {"gameId": game_id}]

    captured: list[list[dict]] = []

    def fake_upsert(_session, model, rows, conflict):
        assert model is PlayByPlay
        assert conflict == ["game_id", "action_number", "action_id"]
        captured.append(rows)
        return len(rows)

    monkeypatch.setattr("scrapers.play_by_play.get_session", lambda: _session(MagicMock()))
    monkeypatch.setattr("scrapers.play_by_play.upsert_rows", fake_upsert)
    written = scrape_play_by_play("2025-26", fetch_actions=fetch)
    assert written == 1
    assert len(captured) == 1
    assert captured[0][0]["action_number"] == 4


@pytest.mark.unit
def test_scrape_play_by_play_game_ids_skips_season_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    season_lookups: list[str] = []
    monkeypatch.setattr(
        "scrapers.play_by_play._final_games_for_season",
        lambda season: (
            season_lookups.append(season) or [{"game_id": "SHOULD_NOT", "season": season}]
        ),
    )
    fetched: list[str] = []

    def fetch(game_id: str) -> list[dict]:
        fetched.append(game_id)
        return [_v3_action(gameId=game_id)]

    monkeypatch.setattr("scrapers.play_by_play.get_session", lambda: _session(MagicMock()))
    monkeypatch.setattr("scrapers.play_by_play.upsert_rows", lambda *args, **kwargs: 1)
    monkeypatch.setattr("scrapers.play_by_play.current_season", lambda today=None: "2025-26")
    written = scrape_play_by_play(game_ids=["0022400001", "0022400099"], fetch_actions=fetch)
    assert written == 2
    assert fetched == ["0022400001", "0022400099"]
    assert season_lookups == []
    assert scrape_play_by_play(game_ids=[], fetch_actions=fetch) == 0
    assert fetched == ["0022400001", "0022400099"]


@pytest.mark.unit
def test_scrape_play_by_play_defaults_current_season(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def fake_finals(season: str) -> list[dict[str, str]]:
        seen.append(season)
        return []

    monkeypatch.setattr("scrapers.play_by_play.current_season", lambda today=None: "2025-26")
    monkeypatch.setattr("scrapers.play_by_play._final_games_for_season", fake_finals)
    with pytest.raises(NoFinalGamesError):
        scrape_play_by_play()
    assert seen == ["2025-26"]


@pytest.mark.unit
def test_actions_from_v3_payload() -> None:
    action = _v3_action()
    assert _actions_from_v3_payload({"game": {"actions": [action]}}) == [action]
    assert _actions_from_v3_payload({"Actions": [action]}) == [action]
    assert _actions_from_v3_payload({"PlayByPlay": [action]}) == [action]
    assert _actions_from_v3_payload({"game": {"Actions": [action]}}) == [action]
    assert _actions_from_v3_payload({"game": {"actions": []}}) == []
    assert _actions_from_v3_payload({"meta": {}, "game": {"gameId": "1"}}) == []
    assert _actions_from_v3_payload({}) == []
    assert _actions_from_v3_payload(None) == []


@pytest.mark.unit
def test_play_by_play_actions_reads_raw_game_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """nba_api 1.11.4 get_normalized_dict() is empty for V3; rows live on game.actions."""

    class Endpoint:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def get_dict(self):
            return {
                "meta": {"version": 1},
                "game": {"gameId": "0022400001", "actions": [_v3_action()]},
            }

        def get_normalized_dict(self):
            return {}

    monkeypatch.setattr("scrapers.play_by_play.nba_call", lambda fn: fn())

    import nba_api.stats.endpoints.playbyplayv3 as playbyplayv3

    monkeypatch.setattr(playbyplayv3, "PlayByPlayV3", Endpoint)
    rows = _play_by_play_actions("0022400001")
    assert rows[0]["actionNumber"] == 4


@pytest.mark.unit
def test_play_by_play_actions_normalized_playbyplay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Endpoint:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def get_dict(self):
            return {}

        def get_normalized_dict(self):
            return {"PlayByPlay": [_v3_action()]}

    monkeypatch.setattr("scrapers.play_by_play.nba_call", lambda fn: fn())

    import nba_api.stats.endpoints.playbyplayv3 as playbyplayv3

    monkeypatch.setattr(playbyplayv3, "PlayByPlayV3", Endpoint)
    rows = _play_by_play_actions("0022400001")
    assert rows[0]["actionNumber"] == 4


@pytest.mark.unit
def test_play_by_play_actions_warns_when_empty(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    class Endpoint:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def get_dict(self):
            return {"meta": {}, "game": {"gameId": "0042500405", "actions": []}}

        def get_normalized_dict(self):
            return {}

    monkeypatch.setattr("scrapers.play_by_play.nba_call", lambda fn: fn())

    import nba_api.stats.endpoints.playbyplayv3 as playbyplayv3

    monkeypatch.setattr(playbyplayv3, "PlayByPlayV3", Endpoint)
    with caplog.at_level("WARNING"):
        rows = _play_by_play_actions("0042500405")
    assert rows == []
    assert "PlayByPlayV3 empty game_id=0042500405" in caplog.text
    assert "raw_keys=['meta', 'game']" in caplog.text
    assert "raw_rowcount=0" in caplog.text


@pytest.mark.unit
def test_scrape_play_by_play_upserts_v3_actions_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[list[dict]] = []

    def fake_upsert(_session, model, rows, conflict):
        assert model is PlayByPlay
        captured.append(rows)
        return len(rows)

    monkeypatch.setattr("scrapers.play_by_play.get_session", lambda: _session(MagicMock()))
    monkeypatch.setattr("scrapers.play_by_play.upsert_rows", fake_upsert)
    monkeypatch.setattr("scrapers.play_by_play.current_season", lambda today=None: "2025-26")
    written = scrape_play_by_play(
        game_ids=["0042500405"],
        fetch_actions=lambda game_id: [
            _v3_action(gameId=game_id, actionNumber=1),
            _v3_action(gameId=game_id, actionNumber=2, actionType="rebound"),
        ],
    )
    assert written == 2
    assert [row["action_number"] for row in captured[0]] == [1, 2]
    assert captured[0][0]["game_id"] == "0042500405"


@pytest.mark.unit
def test_scrape_play_by_play_upserts_duplicate_action_number_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[list[dict]] = []

    def fake_upsert(_session, model, rows, conflict):
        assert model is PlayByPlay
        assert conflict == ["game_id", "action_number", "action_id"]
        captured.append(rows)
        return len(rows)

    monkeypatch.setattr("scrapers.play_by_play.get_session", lambda: _session(MagicMock()))
    monkeypatch.setattr("scrapers.play_by_play.upsert_rows", fake_upsert)
    monkeypatch.setattr("scrapers.play_by_play.current_season", lambda today=None: "2025-26")
    written = scrape_play_by_play(
        game_ids=["0042500405"],
        fetch_actions=lambda game_id: [
            _v3_action(gameId=game_id, actionNumber=4),
            _v3_action(gameId=game_id, actionNumber=4, description="later richer", shotDistance=22),
        ],
    )
    assert written == 1
    assert len(captured) == 1
    assert len(captured[0]) == 1
    assert captured[0][0]["action_number"] == 4
    assert captured[0][0]["description"] == "later richer"


@pytest.mark.unit
def test_scrape_play_by_play_dedupes_same_action_number(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same game_id+action_number+action_id collapses; paired V3 events are kept."""
    captured: list[list[dict]] = []

    def fake_upsert(_session, model, rows, conflict):
        assert model is PlayByPlay
        assert conflict == ["game_id", "action_number", "action_id"]
        captured.append(rows)
        return len(rows)

    monkeypatch.setattr("scrapers.play_by_play.get_session", lambda: _session(MagicMock()))
    monkeypatch.setattr("scrapers.play_by_play.upsert_rows", fake_upsert)
    monkeypatch.setattr("scrapers.play_by_play.current_season", lambda today=None: "2025-26")
    written = scrape_play_by_play(
        game_ids=["0042500405"],
        fetch_actions=lambda game_id: [
            _v3_action(
                gameId=game_id,
                actionNumber=13,
                actionId=9,
                actionType="Turnover",
                subType="Lost Ball",
                description="Castle Lost Ball Turnover (P1.T1)",
            ),
            _v3_action(
                gameId=game_id,
                actionNumber=13,
                actionId=9,
                actionType="Turnover",
                subType="Lost Ball",
                description="Castle Lost Ball Turnover (P1.T1)",
                shotDistance=99,
            ),
            _v3_action(
                gameId=game_id,
                actionNumber=13,
                actionId=10,
                actionType="",
                subType="",
                description="Towns STEAL (1 STL)",
                personId=1626157,
            ),
        ],
    )
    assert written == 2
    assert len(captured) == 1
    rows = captured[0]
    assert [(row["action_number"], row["action_id"]) for row in rows] == [(13, 9), (13, 10)]
    turnover = next(row for row in rows if row["action_id"] == 9)
    assert turnover["extras"]["shotDistance"] == 99
    steal = next(row for row in rows if row["action_id"] == 10)
    assert steal["description"] == "Towns STEAL (1 STL)"


@pytest.mark.unit
def test_scrape_play_by_play_warns_when_mapping_drops_all(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr("scrapers.play_by_play.get_session", lambda: _session(MagicMock()))
    monkeypatch.setattr("scrapers.play_by_play.upsert_rows", lambda *args, **kwargs: 0)
    with caplog.at_level("WARNING"):
        written = scrape_play_by_play(
            "2025-26",
            game_ids=["0042500405"],
            fetch_actions=lambda _game_id: [{"gameId": "0042500405", "period": 1}],
        )
    assert written == 0
    assert "produced no rows game_id=0042500405" in caplog.text
    assert "raw_rowcount=1" in caplog.text
    assert "sample_keys=" in caplog.text


@pytest.mark.unit
def test_cli_scrape_play_by_play(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    def fake(season=None, game_ids=None):
        calls.append({"season": season, "game_ids": game_ids})
        return 12

    monkeypatch.setattr("main.scrape_play_by_play", fake)
    monkeypatch.setattr("main.current_season", lambda: "2025-26")
    runner = CliRunner()
    defaulted = runner.invoke(cli, ["scrape-play-by-play"])
    assert defaulted.exit_code == 0
    assert "12" in defaulted.output
    assert "2025-26" in defaulted.output
    assert calls[0]["game_ids"] is None
    explicit = runner.invoke(cli, ["scrape-play-by-play", "--season", "2024-25"])
    assert explicit.exit_code == 0
    assert "2024-25" in explicit.output
    targeted = runner.invoke(
        cli,
        ["scrape-play-by-play", "--game-id", "0042500405", "--game-id", "0042500404"],
    )
    assert targeted.exit_code == 0
    assert "2 game(s)" in targeted.output
    assert calls[-1]["game_ids"] == ["0042500405", "0042500404"]


@pytest.mark.unit
def test_cli_scrape_play_by_play_no_games(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(season=None, game_ids=None):
        raise NoFinalGamesError(
            "No Final games in source.games for 2025-26; run scrape-games first."
        )

    monkeypatch.setattr("main.scrape_play_by_play", boom)
    result = CliRunner().invoke(cli, ["scrape-play-by-play"])
    assert result.exit_code != 0
    assert "No Final games" in result.output
    assert "Traceback" not in result.output
