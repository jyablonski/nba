from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from main import cli
from scrapers.injuries import scrape_injuries
from scrapers.injuries_parse import (
    INJURIES_URL,
    bref_team_from_label,
    parse_injuries_html,
    parse_update_date,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "injuries"


def _html(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@contextmanager
def _session(mock_session):
    yield mock_session


@pytest.mark.unit
def test_parse_update_date_formats() -> None:
    assert parse_update_date("2026-09-03") == date(2026, 9, 3)
    assert parse_update_date("Thu, Sep 3, 2026") == date(2026, 9, 3)
    assert parse_update_date("Sep 3, 2026") == date(2026, 9, 3)
    assert parse_update_date("") is None
    assert parse_update_date("not-a-date") is None
    assert parse_update_date(date(2026, 1, 1)) == date(2026, 1, 1)
    from datetime import datetime

    assert parse_update_date(datetime(2026, 2, 3, 4, 5)) == date(2026, 2, 3)


@pytest.mark.unit
def test_bref_team_from_label_maps_city_and_abbr() -> None:
    assert bref_team_from_label("Golden State") == "GSW"
    assert bref_team_from_label("LA Clippers") == "LAC"
    assert bref_team_from_label("BKN") == "BRK"
    assert bref_team_from_label("PHX") == "PHO"
    assert bref_team_from_label("Atlantis") is None


@pytest.mark.unit
def test_parse_injuries_html_fixture() -> None:
    rows = parse_injuries_html(_html("injuries.html"), source_url=INJURIES_URL)
    assert len(rows) == 2
    curry = next(row for row in rows if row["player_name"] == "Stephen Curry")
    assert curry["bref_player_slug"] == "curryst01"
    assert curry["bref_team_abbreviation"] == "GSW"
    assert curry["nba_team_abbreviation"] == "GSW"
    assert curry["update_date"] == date(2026, 9, 3)
    assert "Ankle" in curry["description"]
    kawhi = next(row for row in rows if row["player_name"] == "Kawhi Leonard")
    assert kawhi["bref_team_abbreviation"] == "LAC"
    assert kawhi["nba_team_abbreviation"] == "LAC"


@pytest.mark.unit
def test_parse_injuries_comment_wrapped() -> None:
    rows = parse_injuries_html(_html("comment_wrapped.html"))
    assert len(rows) == 1
    assert rows[0]["player_name"] == "LeBron James"
    assert rows[0]["bref_team_abbreviation"] == "LAL"


@pytest.mark.unit
def test_parse_injuries_empty_without_table() -> None:
    assert parse_injuries_html("<html><body>no table</body></html>") == []


@pytest.mark.unit
def test_scrape_injuries_upserts_and_deletes_stale(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    monkeypatch.setattr("scrapers.injuries.get_session", lambda: _session(session))
    captured: list[list[dict]] = []

    def fake_upsert(_session, _model, rows, _conflict):
        captured.append(rows)
        return len(rows)

    monkeypatch.setattr("scrapers.injuries.upsert_rows", fake_upsert)
    count = scrape_injuries(fetch_html=lambda url: _html("injuries.html"))
    assert count == 2
    assert captured[0][0]["scraped_at"] is not None
    session.execute.assert_called()
    session.commit.assert_called()


@pytest.mark.unit
def test_cli_scrape_injuries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("main.scrape_injuries", lambda: 4)
    result = CliRunner().invoke(cli, ["scrape-injuries"])
    assert result.exit_code == 0
    assert "4" in result.output
