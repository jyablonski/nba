from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from main import cli, main
from scrapers.players import parse_roster_html
from scrapers.teams import scrape_teams


@contextmanager
def _session(mock_session):
    yield mock_session


ROSTER_HTML = """
<table id="roster"><tbody>
  <tr><th data-stat="player"><a href="/players/c/curryst01.html">Stephen Curry</a></th>
  <td data-stat="number">30</td><td data-stat="pos">PG</td><td data-stat="height">6-2</td>
  <td data-stat="weight">185</td><td data-stat="birth_date">1988-03-14</td><td data-stat="years">2010-2025</td></tr>
</tbody></table>
"""


@pytest.mark.unit
def test_scrape_teams_uses_repo_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    monkeypatch.setattr("scrapers.teams.get_session", lambda: _session(session))
    monkeypatch.setattr("scrapers.teams.seed_team_catalog", lambda _session: 30)
    assert scrape_teams() == 30


@pytest.mark.unit
def test_parse_roster_html_emits_bref_external_id() -> None:
    rows = parse_roster_html(ROSTER_HTML, team_id="team-id", source_url="https://example.test")
    assert rows[0]["provider"] == "basketball-reference"
    assert rows[0]["external_id"] == "curryst01"
    assert rows[0]["team_id"] == "team-id"
    assert rows[0]["weight"] == 185


@pytest.mark.unit
def test_parse_roster_comment_wrapper_and_invalid_birth_date() -> None:
    html = '<!-- <table id="roster"><tbody><tr><th data-stat="player"><a href="/players/x/testpl01.html">Test Player</a></th><td data-stat="birth_date">bad</td></tr></tbody></table> -->'
    rows = parse_roster_html(html, team_id="team-id", source_url="https://example.test")
    assert rows[0]["external_id"] == "testpl01"
    assert rows[0]["birth_date"] is None
    assert (
        parse_roster_html("<html></html>", team_id="team-id", source_url="https://example.test")
        == []
    )


@pytest.mark.unit
def test_scrape_players_fetches_bref_rosters(monkeypatch: pytest.MonkeyPatch) -> None:
    import catalog.teams

    entry = catalog.teams.TEAM_CATALOG[0]
    player_id = "player-id"
    session = MagicMock()
    session.get.return_value = MagicMock()
    monkeypatch.setattr("catalog.teams.TEAM_CATALOG", (entry,))
    monkeypatch.setattr("scrapers.players.get_session", lambda: _session(session))
    monkeypatch.setattr("scrapers.players.seed_team_catalog", lambda *args, **kwargs: 1)
    monkeypatch.setattr("scrapers.players.ensure_player", lambda *args, **kwargs: player_id)
    assert (
        __import__("scrapers.players", fromlist=["scrape_players"]).scrape_players(
            season="2024-25", fetch_html=lambda url: ROSTER_HTML
        )
        == 1
    )


@pytest.mark.unit
def test_cli_entrypoint_and_core_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[bool] = []
    monkeypatch.setattr("main.cli", lambda: called.append(True))
    main()
    assert called == [True]

    monkeypatch.setattr("main.scrape_teams", lambda: 30)
    monkeypatch.setattr("main.scrape_players", lambda: 10)
    monkeypatch.setattr("main.scrape_games", lambda season: 82)
    monkeypatch.setattr("main.scrape_player_game_logs", lambda season, active_only=False: 5)
    monkeypatch.setattr("main.scrape_standings", lambda season: 30)
    runner = CliRunner()
    assert runner.invoke(cli, ["scrape-teams"]).exit_code == 0
    assert runner.invoke(cli, ["scrape-players"]).exit_code == 0
    assert runner.invoke(cli, ["scrape-games", "--season", "2024-25"]).exit_code == 0
    assert runner.invoke(cli, ["scrape-game-logs", "--season", "2024-25"]).exit_code == 0
    assert runner.invoke(cli, ["scrape-standings", "--season", "2024-25"]).exit_code == 0
