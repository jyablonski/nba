from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from scrapers.standings import parse_standings_html, scrape_standings, standings_url

STANDINGS_HTML = """
<table id="standings_e"><tbody>
  <tr><th data-stat="ranker">1</th><th data-stat="team_name"><a href="/teams/BOS/2025.html">Boston Celtics</a></th>
  <td data-stat="wins">10</td><td data-stat="losses">2</td><td data-stat="win_loss_pct">.833</td>
  <td data-stat="gb">-</td><td data-stat="current_streak">W 3</td><td data-stat="last_10">8-2</td></tr>
</tbody></table>
"""


@contextmanager
def _session(mock_session):
    yield mock_session


@pytest.mark.unit
def test_parse_standings_html() -> None:
    rows = parse_standings_html(
        STANDINGS_HTML,
        season="2024-25",
        as_of_date=date(2024, 12, 1),
        source_url="https://www.basketball-reference.com/leagues/NBA_2025_standings.html",
    )
    assert rows == [
        {
            "bref_team_abbreviation": "BOS",
            "season": "2024-25",
            "season_type": "Regular Season",
            "as_of_date": date(2024, 12, 1),
            "conference": "East",
            "division": None,
            "conference_rank": 1,
            "division_rank": None,
            "wins": 10,
            "losses": 2,
            "win_pct": 0.833,
            "games_back": None,
            "conf_games_back": None,
            "streak": "W 3",
            "last_10": "8-2",
            "source_url": "https://www.basketball-reference.com/leagues/NBA_2025_standings.html",
        }
    ]
    assert standings_url("2024-25").endswith("/leagues/NBA_2025_standings.html")


@pytest.mark.unit
def test_parse_standings_ignores_division_tables() -> None:
    html = """
    <table id="confs_standings_E"><tbody>
      <tr><th data-stat="ranker">1</th><th data-stat="team_name"><a href="/teams/BOS/2025.html">Boston Celtics</a></th>
      <td data-stat="wins">10</td><td data-stat="losses">2</td><td data-stat="win_loss_pct">.833</td>
      </tr>
    </tbody></table>
    <table id="divs_standings_E"><tbody>
      <tr><th data-stat="ranker">1</th><th data-stat="team_name"><a href="/teams/BOS/2025.html">Boston Celtics</a></th>
      <td data-stat="wins">10</td><td data-stat="losses">2</td><td data-stat="win_loss_pct">.833</td>
      </tr>
    </tbody></table>
    """
    rows = parse_standings_html(
        html,
        season="2024-25",
        as_of_date=date(2024, 12, 1),
        source_url="https://www.basketball-reference.com/leagues/NBA_2025_standings.html",
    )
    assert len(rows) == 1


@pytest.mark.unit
def test_scrape_standings_canonicalizes_teams(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    team_id = uuid4()
    captured: list[dict] = []
    monkeypatch.setattr("scrapers.standings.get_session", lambda: _session(session))
    monkeypatch.setattr("scrapers.standings.seed_team_catalog", lambda *args, **kwargs: 30)
    monkeypatch.setattr(
        "scrapers.standings.resolve_team_id",
        lambda _session, code: team_id if code == "BOS" else None,
    )
    monkeypatch.setattr(
        "scrapers.standings.upsert_rows",
        lambda _s, _m, rows, _c: captured.extend(rows) or len(rows),
    )
    assert scrape_standings("2024-25", fetch_html=lambda url: STANDINGS_HTML) == 1
    assert captured[0]["team_id"] == team_id
    assert captured[0]["games_back"] is None
