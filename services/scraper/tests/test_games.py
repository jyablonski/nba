from contextlib import contextmanager
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from scrapers.games import (
    _is_final_status,
    _schedule_page_urls,
    parse_schedule_html,
    schedule_url,
    scrape_games,
)

SCHEDULE_HTML = """
<table id="schedule"><tbody>
  <tr>
    <td data-stat="date_game" csk="2024-10-22">Tue, Oct 22, 2024</td>
    <td data-stat="visitor_team_name"><a href="/teams/LAL/2025.html">Los Angeles Lakers</a></td>
    <td data-stat="visitor_pts">110</td>
    <td data-stat="home_team_name"><a href="/teams/GSW/2025.html">Golden State Warriors</a></td>
    <td data-stat="home_pts">122</td>
    <td data-stat="arena_name">Chase Center</td>
    <td data-stat="box_score_text"><a href="/boxscores/202410220GSW.html">Box Score</a></td>
  </tr>
</tbody></table>
"""


@contextmanager
def _session(mock_session):
    yield mock_session


@pytest.mark.unit
def test_parse_schedule_html_and_url() -> None:
    rows = parse_schedule_html(
        SCHEDULE_HTML,
        season="2024-25",
        source_url="https://www.basketball-reference.com/leagues/NBA_2025_games.html",
    )
    assert len(rows) == 1
    assert rows[0]["external_id"] == "202410220GSW"
    assert rows[0]["home_bref_abbreviation"] == "GSW"
    assert rows[0]["away_bref_abbreviation"] == "LAL"
    assert rows[0]["status"] == "Final"
    assert schedule_url("2024-25").endswith("/leagues/NBA_2025_games.html")


@pytest.mark.unit
def test_parse_schedule_skips_invalid_rows() -> None:
    assert (
        parse_schedule_html(
            '<table id="schedule"><tbody><tr><td data-stat="date_game">bad</td></tr></tbody></table>',
            season="2024-25",
            source_url="https://example.test",
        )
        == []
    )


@pytest.mark.unit
def test_parse_schedule_uses_visible_date_when_csk_is_game_key() -> None:
    html = SCHEDULE_HTML.replace('csk="2024-10-22"', 'csk="202410220GSW"')
    rows = parse_schedule_html(
        html,
        season="2024-25",
        source_url="https://example.test",
    )
    assert len(rows) == 1
    assert rows[0]["game_date"].isoformat() == "2024-10-22"


@pytest.mark.unit
def test_parse_schedule_classifies_postseason_rows() -> None:
    html = """
    <table id="schedule"><tbody>
      <tr>
        <td data-stat="date_game" csk="2026-04-12">Sun, Apr 12, 2026</td>
        <td data-stat="visitor_team_name"><a href="/teams/LAL/2026.html">LAL</a></td>
        <td data-stat="visitor_pts">110</td>
        <td data-stat="home_team_name"><a href="/teams/GSW/2026.html">GSW</a></td>
        <td data-stat="home_pts">122</td>
        <td data-stat="box_score_text"><a href="/boxscores/202604120GSW.html">Box</a></td>
      </tr>
      <tr>
        <td data-stat="date_game" csk="2026-04-14">Tue, Apr 14, 2026</td>
        <td data-stat="visitor_team_name"><a href="/teams/MIA/2026.html">MIA</a></td>
        <td data-stat="visitor_pts">126</td>
        <td data-stat="home_team_name"><a href="/teams/CHO/2026.html">CHO</a></td>
        <td data-stat="home_pts">127</td>
        <td data-stat="game_remarks">Play-In Game</td>
        <td data-stat="box_score_text"><a href="/boxscores/202604140CHO.html">Box</a></td>
      </tr>
      <tr>
        <td data-stat="date_game" csk="2026-04-18">Sat, Apr 18, 2026</td>
        <td data-stat="visitor_team_name"><a href="/teams/LAL/2026.html">LAL</a></td>
        <td data-stat="visitor_pts">110</td>
        <td data-stat="home_team_name"><a href="/teams/DEN/2026.html">DEN</a></td>
        <td data-stat="home_pts">122</td>
        <td data-stat="box_score_text"><a href="/boxscores/202604180DEN.html">Box</a></td>
      </tr>
    </tbody></table>
    """
    rows = parse_schedule_html(html, season="2025-26", source_url="https://example.test/april")
    assert [row["season_type"] for row in rows] == ["Regular Season", "PlayIn", "Playoffs"]


@pytest.mark.unit
def test_schedule_page_urls_discovers_monthly_pages() -> None:
    base = schedule_url("2024-25")
    html = '<a href="/leagues/NBA_2025_games-november.html">November</a>'
    assert _schedule_page_urls(html, "2024-25", base) == [
        base,
        "https://www.basketball-reference.com/leagues/NBA_2025_games-november.html",
    ]


@pytest.mark.unit
def test_scrape_games_resolves_canonical_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    team_ids = {"GSW": uuid4(), "LAL": uuid4()}
    resolved: list[dict] = []
    monkeypatch.setattr("scrapers.games.get_session", lambda: _session(session))
    monkeypatch.setattr("scrapers.games.seed_team_catalog", lambda *args, **kwargs: 30)
    monkeypatch.setattr("scrapers.games.resolve_team_id", lambda _session, code: team_ids[code])
    monkeypatch.setattr(
        "scrapers.games.resolve_game", lambda _session, **kwargs: resolved.append(kwargs) or uuid4()
    )
    written = scrape_games("2024-25", fetch_html=lambda url: SCHEDULE_HTML)
    assert written == 1
    assert resolved[0]["home_team_id"] == team_ids["GSW"]
    assert resolved[0]["away_team_id"] == team_ids["LAL"]
    assert resolved[0]["external_id"] == "202410220GSW"


@pytest.mark.unit
def test_scrape_games_fetches_monthly_pages_and_deduplicates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_url = schedule_url("2024-25")
    month_url = base_url.replace("_games.html", "_games-november.html")
    calls: list[str] = []
    session = MagicMock()
    monkeypatch.setattr("scrapers.games.get_session", lambda: _session(session))
    monkeypatch.setattr("scrapers.games.seed_team_catalog", lambda *args, **kwargs: 30)
    team_ids = {"GSW": uuid4(), "LAL": uuid4()}
    monkeypatch.setattr("scrapers.games.resolve_team_id", lambda _session, code: team_ids[code])
    monkeypatch.setattr("scrapers.games.resolve_game", lambda *args, **kwargs: uuid4())

    def fetch(url: str) -> str:
        calls.append(url)
        if url == base_url:
            return SCHEDULE_HTML.replace(
                "</table>",
                '</table><a href="/leagues/NBA_2025_games-november.html">November</a>',
            )
        return SCHEDULE_HTML

    assert scrape_games("2024-25", fetch_html=fetch) == 1
    assert calls == [base_url, month_url]


@pytest.mark.unit
def test_final_status_is_bref_text_only() -> None:
    assert _is_final_status("Final") is True
    assert _is_final_status("Scheduled") is False
