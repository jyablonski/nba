from __future__ import annotations

import time
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from scrapers.contracts import (
    BrefHTTPError,
    bref_get,
    bref_rate_limit,
    scrape_contracts,
    team_contracts_url,
)
from scrapers.contracts_parse import (
    BREF_TEAM_ABBREVIATIONS,
    bref_team_abbreviation,
    nba_team_abbreviation,
    normalize_player_name,
    parse_contracts_html,
    parse_salary_text,
    parse_team_list,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "contracts"


def _html(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.unit
def test_normalize_player_name_folds_diacritics_and_suffixes() -> None:
    assert normalize_player_name("Kristaps Porziņģis") == "kristaps porzingis"
    assert normalize_player_name("Tim Hardaway Jr.") == "tim hardaway"
    assert normalize_player_name("Karl-Anthony Towns") == "karl anthony towns"


@pytest.mark.unit
def test_team_abbreviation_mapping() -> None:
    assert nba_team_abbreviation("BRK") == "BKN"
    assert nba_team_abbreviation("GSW") == "GSW"
    assert bref_team_abbreviation("PHX") == "PHO"
    assert bref_team_abbreviation("LAL") == "LAL"


@pytest.mark.unit
def test_parse_team_list_defaults_and_maps_nba_codes() -> None:
    assert parse_team_list(None) == list(BREF_TEAM_ABBREVIATIONS)
    assert parse_team_list("GSW, PHX, BKN") == ["GSW", "PHO", "BRK"]
    with pytest.raises(ValueError, match="Unknown"):
        parse_team_list("SEA")
    with pytest.raises(ValueError, match="No team"):
        parse_team_list(" , ")


@pytest.mark.unit
def test_parse_team_list_dedupes() -> None:
    assert parse_team_list("GSW, gsw, GSW") == ["GSW"]


@pytest.mark.unit
def test_parse_csk_only_player_and_no_table_header() -> None:
    html = """
    <table id="contracts">
      <tr>
        <th data-stat="player">Player</th>
        <th data-stat="y1">2024-25</th>
      </tr>
      <tbody>
        <tr>
          <th data-stat="player" csk="smithjo01">Joe Smith</th>
          <td data-stat="y1" csk="123">$123</td>
        </tr>
      </tbody>
    </table>
    """
    players, payroll = parse_contracts_html(
        html, bref_team_abbreviation="BRK", source_url="https://example.test/BRK.html"
    )
    assert players[0]["bref_player_slug"] == "smithjo01"
    assert players[0]["nba_team_abbreviation"] == "BKN"
    assert payroll == []


@pytest.mark.unit
def test_scrape_contracts_fetches_each_team(monkeypatch: pytest.MonkeyPatch) -> None:
    urls: list[str] = []

    def fake_fetch(url: str) -> str:
        urls.append(url)
        return "<html></html>"

    monkeypatch.setattr("scrapers.contracts.get_session", lambda: _session(MagicMock()))
    monkeypatch.setattr("scrapers.contracts.upsert_rows", lambda *args, **kwargs: 0)
    scrape_contracts("GSW,LAC", fetch_html=fake_fetch)
    assert urls == [
        "https://www.basketball-reference.com/contracts/GSW.html",
        "https://www.basketball-reference.com/contracts/LAC.html",
    ]
    assert parse_salary_text("$62,587,158") == 62587158
    assert parse_salary_text("") is None
    assert parse_salary_text(None) is None
    assert parse_salary_text("-") is None


@pytest.mark.unit
def test_parse_gsw_fixture_unpivots_seasons_and_totals() -> None:
    players, payroll = parse_contracts_html(
        _html("gsw_contracts.html"),
        bref_team_abbreviation="GSW",
        source_url="https://www.basketball-reference.com/contracts/GSW.html",
    )
    by_key = {(row["bref_player_slug"], row["season"]): row for row in players}
    curry = by_key[("curryst01", "2026-27")]
    assert curry["player_name"] == "Stephen Curry"
    assert curry["salary"] == 62587158
    assert curry["is_fully_guaranteed"] is True
    assert curry["nba_team_abbreviation"] == "GSW"

    porzingis_y2 = by_key[("porzikr01", "2027-28")]
    assert porzingis_y2["player_name_normalized"] == "kristaps porzingis"
    assert porzingis_y2["salary"] == 20487805

    niang = by_key[("niangge01", "2026-27")]
    assert niang["is_fully_guaranteed"] is False
    assert niang["remaining_guaranteed"] is None

    assert ("curryst01", "2027-28") not in by_key
    assert len(payroll) == 2
    payroll_by_season = {row["season"]: row for row in payroll}
    assert payroll_by_season["2026-27"]["total_salary"] == 84548774
    assert payroll_by_season["2027-28"]["remaining_guaranteed"] == 82099353


@pytest.mark.unit
def test_parse_comment_wrapped_table() -> None:
    players, payroll = parse_contracts_html(
        _html("comment_wrapped.html"),
        bref_team_abbreviation="LAC",
        source_url="https://www.basketball-reference.com/contracts/LAC.html",
    )
    assert len(players) == 1
    assert players[0]["bref_player_slug"] == "leonaka01"
    assert players[0]["salary"] == 45000000
    assert payroll[0]["nba_team_abbreviation"] == "LAC"
    assert payroll[0]["total_salary"] == 45000000


@pytest.mark.unit
def test_parse_missing_table_returns_empty() -> None:
    players, payroll = parse_contracts_html(
        "<html><body><p>no table</p></body></html>",
        bref_team_abbreviation="GSW",
        source_url="https://example.test",
    )
    assert players == []
    assert payroll == []


@pytest.mark.unit
def test_scrape_contracts_upserts_parsed_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    html = _html("gsw_contracts.html")
    captured: list[tuple] = []

    def fake_upsert(_session, model, rows, conflict):
        captured.append((model.__name__, len(rows), list(conflict)))
        return len(rows)

    monkeypatch.setattr("scrapers.contracts.get_session", lambda: _session(MagicMock()))
    monkeypatch.setattr("scrapers.contracts.upsert_rows", fake_upsert)
    n_players, n_payroll = scrape_contracts("GSW", fetch_html=lambda url: html)
    assert n_players == 4  # Curry 1 + Porzingis 2 + Niang 1
    assert n_payroll == 2
    assert captured[0][0] == "PlayerContract"
    assert captured[1][0] == "TeamPayroll"


@pytest.mark.unit
def test_bref_get_and_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    import scrapers.contracts as contracts_mod

    monkeypatch.setattr(contracts_mod, "BREF_REQUEST_DELAY_SECONDS", 0)
    monkeypatch.setattr(contracts_mod, "_last_bref_request_at", 0.0)
    slept: list[float] = []
    monkeypatch.setattr("scrapers.contracts.time.sleep", lambda seconds: slept.append(seconds))
    bref_rate_limit()
    monkeypatch.setattr(contracts_mod, "BREF_REQUEST_DELAY_SECONDS", 1)
    monkeypatch.setattr(contracts_mod, "_last_bref_request_at", time.monotonic())
    bref_rate_limit()
    assert slept
    response = SimpleNamespace(status_code=200, text="<html>ok</html>")
    monkeypatch.setattr(
        "scrapers.contracts.requests.get",
        lambda *args, **kwargs: response,
    )
    monkeypatch.setattr(contracts_mod, "BREF_REQUEST_DELAY_SECONDS", 0)
    assert bref_get("https://example.test/x") == "<html>ok</html>"
    error = SimpleNamespace(status_code=403, text="nope")
    with pytest.raises(BrefHTTPError, match="HTTP 403"):
        bref_get("https://example.test/x", get=lambda *args, **kwargs: error)


@pytest.mark.unit
def test_cli_scrape_contracts_bad_team() -> None:
    from main import cli

    result = CliRunner().invoke(cli, ["scrape-contracts", "--teams", "SEA"])
    assert result.exit_code != 0


@pytest.mark.unit
def test_team_contracts_url() -> None:
    assert team_contracts_url("gsw") == "https://www.basketball-reference.com/contracts/GSW.html"


@pytest.mark.unit
def test_cli_scrape_contracts(monkeypatch: pytest.MonkeyPatch) -> None:
    from main import cli

    monkeypatch.setattr("main.scrape_contracts", lambda teams=None: (12, 3))
    result = CliRunner().invoke(cli, ["scrape-contracts", "--teams", "GSW"])
    assert result.exit_code == 0
    assert "12" in result.output
    assert "3" in result.output


@contextmanager
def _session(mock_session):
    yield mock_session
