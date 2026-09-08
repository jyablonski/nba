from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from scrapers.play_by_play import (
    NoFinalGamesError,
    map_play_by_play_action,
    parse_play_by_play_html,
    play_by_play_url,
    scrape_play_by_play,
)


@contextmanager
def _session(mock_session):
    yield mock_session


PBP_HTML = """
<table id="pbp"><tbody>
  <tr>
    <td data-stat="quarter">1</td><td data-stat="time">11:32</td>
    <td data-stat="home_score">2</td><td data-stat="away_score">0</td>
    <td data-stat="a1">Stephen Curry makes 2-pt shot</td>
    <td data-stat="a2">Golden State Warriors</td>
    <td><a href="/players/c/curryst01.html">Stephen Curry</a><a href="/teams/GSW/2025.html">GSW</a></td>
  </tr>
</tbody></table>
"""

LIVE_PBP_HTML = """
<table id="pbp"><tbody>
  <tr class="thead" id="q1"><th colspan="6">1st Q</th></tr>
  <tr class="thead"><th>Time</th><th>Houston</th><th></th><th>Score</th><th></th><th>Oklahoma City</th></tr>
  <tr>
    <td>11:32.0</td>
    <td><a href="/players/c/curryst01.html">Stephen Curry makes 2-pt shot</a></td>
    <td></td><td>2-0</td><td></td><td></td>
  </tr>
  <tr>
    <td>11:01.0</td><td></td><td></td><td>2-2</td><td></td>
    <td><a href="/players/d/duranke01.html">Kevin Durant makes 2-pt shot</a></td>
  </tr>
</tbody></table>
"""


@pytest.mark.unit
def test_parse_bref_play_by_play_html() -> None:
    game_id = uuid4()
    rows = parse_play_by_play_html(PBP_HTML, game_id=game_id, season="2024-25")
    assert len(rows) == 1
    assert rows[0]["game_id"] == game_id
    assert rows[0]["player_external_id"] == "curryst01"
    assert rows[0]["team_bref_abbreviation"] == "GSW"
    assert rows[0]["description"] == "Stephen Curry makes 2-pt shot | Golden State Warriors"
    assert parse_play_by_play_html("<html></html>", game_id=game_id, season="2024-25") == []
    assert play_by_play_url("202410220GSW").endswith("/boxscores/pbp/202410220GSW.html")


@pytest.mark.unit
def test_parse_live_bref_play_by_play_layout() -> None:
    rows = parse_play_by_play_html(
        LIVE_PBP_HTML,
        game_id=uuid4(),
        season="2025-26",
        home_bref_abbreviation="OKC",
        away_bref_abbreviation="HOU",
    )
    assert len(rows) == 2
    assert rows[0]["period"] == 1
    assert rows[0]["clock"] == "11:32.0"
    assert rows[0]["score_home"] == 0
    assert rows[0]["score_away"] == 2
    assert rows[0]["team_bref_abbreviation"] == "HOU"
    assert rows[1]["team_bref_abbreviation"] == "OKC"

    jump_ball = LIVE_PBP_HTML.replace(
        "</tbody>",
        "<tr><td>12:00.0</td><td>Jump ball</td></tr></tbody>",
    )
    jump_rows = parse_play_by_play_html(
        jump_ball,
        game_id=uuid4(),
        season="2025-26",
        home_bref_abbreviation="OKC",
        away_bref_abbreviation="HOU",
    )
    assert jump_rows[-1]["description"] == "Jump ball"
    assert jump_rows[-1]["score_home"] is None


@pytest.mark.unit
def test_map_play_by_play_action_normalizes_values() -> None:
    game_id = uuid4()
    stamp = datetime.now()
    row = map_play_by_play_action(
        {
            "action_number": "4",
            "action_id": "5",
            "period": "1",
            "score_home": "2",
            "description": "shot",
        },
        game_id=game_id,
        season="2024-25",
        scraped_at=stamp,
    )
    assert row is not None
    assert row["game_id"] == game_id
    assert row["action_number"] == 4
    assert row["action_id"] == 5
    assert row["score_home"] == 2
    assert row["scraped_at"] == stamp
    assert map_play_by_play_action({}, game_id=game_id, season="2024-25", scraped_at=stamp) is None


@pytest.mark.unit
def test_scrape_play_by_play_requires_completed_games(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("scrapers.play_by_play._final_games_for_season", lambda season: [])
    with pytest.raises(NoFinalGamesError, match="2024-25"):
        scrape_play_by_play("2024-25")


@pytest.mark.unit
def test_scrape_play_by_play_resolves_player_and_upserts(monkeypatch: pytest.MonkeyPatch) -> None:
    game_id = uuid4()
    home_team_id, away_team_id = uuid4(), uuid4()
    game = SimpleNamespace(
        game_id=game_id,
        season="2024-25",
        home_team_id=home_team_id,
        away_team_id=away_team_id,
    )
    external = SimpleNamespace(game_id=game_id, external_id="202410220GSW")
    first, second = MagicMock(), MagicMock()
    game_query, team_query = MagicMock(), MagicMock()
    game_query.filter.return_value.all.return_value = [game]
    team_query.filter.return_value.all.return_value = [
        SimpleNamespace(team_id=home_team_id, abbreviation="GSW"),
        SimpleNamespace(team_id=away_team_id, abbreviation="LAL"),
    ]
    first.query.side_effect = [game_query, team_query]
    first.scalars.side_effect = [
        SimpleNamespace(all=lambda: [external]),
        SimpleNamespace(all=lambda: []),
    ]
    captured: list[list[dict]] = []
    monkeypatch.setattr(
        "scrapers.play_by_play.get_session",
        lambda: iter((_session(first), _session(second))).__next__(),
    )
    monkeypatch.setattr("scrapers.play_by_play.seed_team_catalog", lambda *args, **kwargs: 30)
    team_id = uuid4()
    monkeypatch.setattr(
        "scrapers.play_by_play.resolve_team_id",
        lambda _session, code: team_id if code == "GSW" else None,
    )
    monkeypatch.setattr("scrapers.play_by_play.ensure_player", lambda *args, **kwargs: uuid4())
    monkeypatch.setattr(
        "scrapers.play_by_play.upsert_rows",
        lambda _s, _m, rows, _c: captured.append(rows) or len(rows),
    )
    written = scrape_play_by_play(
        game_ids=[game_id],
        fetch_actions=lambda external_id: [
            {
                "action_number": 1,
                "team_bref_abbreviation": "GSW",
                "player_external_id": "curryst01",
                "player_name": "Stephen Curry",
                "description": "shot",
            }
        ],
    )
    assert written == 1
    assert captured[0][0]["team_id"] == team_id
