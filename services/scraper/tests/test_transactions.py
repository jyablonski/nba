from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from main import cli
from scrapers.transactions import scrape_transactions
from scrapers.transactions_parse import (
    parse_participants,
    parse_transaction_date,
    parse_transactions_html,
    transaction_key,
    transactions_url,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "transactions"
SEASON = "2025-26"
SOURCE_URL = "https://www.basketball-reference.com/leagues/NBA_2026_transactions.html"


def _html(name: str = "nba_2026_transactions.html") -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def parsed() -> list[dict]:
    return parse_transactions_html(_html(), season=SEASON, source_url=SOURCE_URL)


@pytest.mark.unit
def test_transactions_url_uses_season_end_year() -> None:
    assert transactions_url(2026, "https://x") == "https://x/leagues/NBA_2026_transactions.html"


@pytest.mark.unit
def test_transaction_key_is_stable_and_content_sensitive() -> None:
    day = date(2025, 7, 1)
    first = transaction_key(day, "The Toronto Raptors signed Garrett Temple.")
    assert first == transaction_key(day, "The Toronto Raptors signed Garrett Temple.")
    # One character of description changes the grain...
    assert first != transaction_key(day, "The Toronto Raptors signed Garrett Templo.")
    # ...and so does the date, so a repeated description stays two rows.
    assert first != transaction_key(date(2025, 7, 2), "The Toronto Raptors signed Garrett Temple.")
    assert len(first) == 64


@pytest.mark.unit
def test_parse_transaction_date() -> None:
    assert parse_transaction_date("July 1, 2025") == date(2025, 7, 1)
    assert parse_transaction_date(" February 25, 2025 ") == date(2025, 2, 25)
    assert parse_transaction_date("not a date") is None


@pytest.mark.unit
def test_parses_every_entry_on_the_page(parsed: list[dict]) -> None:
    """The page's last <li> is unclosed, so a paired-tag regex drops it."""
    assert len(parsed) == 1130
    assert len({row["transaction_key"] for row in parsed}) == 1130
    # The unclosed final group.
    last = parsed[-1]
    assert last["transaction_date"] == date(2026, 7, 9)
    assert last["description"] == "The Golden State Warriors signed Charles Bassey."


@pytest.mark.unit
def test_rows_carry_season_and_source(parsed: list[dict]) -> None:
    assert {row["season"] for row in parsed} == {SEASON}
    assert {row["source_url"] for row in parsed} == {SOURCE_URL}


@pytest.mark.unit
def test_dates_come_from_the_page_not_the_season(parsed: list[dict]) -> None:
    """Entries fall outside the season window, so the year must be read, not derived."""
    dates = [row["transaction_date"] for row in parsed]
    assert min(dates) == date(2025, 2, 25)
    assert max(dates) == date(2026, 7, 9)


@pytest.mark.unit
def test_simple_signing_participants(parsed: list[dict]) -> None:
    row = parsed[0]
    assert row["participants"] == [
        {
            "participant_type": "team",
            "direction": "to",
            "bref_slug": "MIN",
            "display_name": "Minnesota Timberwolves",
        },
        {
            "participant_type": "player",
            "direction": "none",
            "bref_slug": "bernaju01",
            "display_name": "Jules Bernard",
        },
    ]


@pytest.mark.unit
def test_multi_team_trade_keeps_both_directions(parsed: list[dict]) -> None:
    """A team sending and receiving in one trade is two rows, not one."""
    trade = max(parsed, key=lambda row: len(row["participants"]))
    teams = [p for p in trade["participants"] if p["participant_type"] == "team"]
    atlanta = {p["direction"] for p in teams if p["bref_slug"] == "ATL"}
    assert atlanta == {"from", "to"}
    assert {p["direction"] for p in teams} <= {"from", "to"}
    players = [p for p in trade["participants"] if p["participant_type"] == "player"]
    assert {p["direction"] for p in players} == {"none"}


@pytest.mark.unit
def test_draft_picks_are_not_participants() -> None:
    entry = (
        'the <a data-attr-from="HOU" href="/teams/HOU/2026.html">Houston Rockets</a> '
        "traded cash and a 2031 2nd round draft pick to the "
        '<a data-attr-to="ATL" href="/teams/ATL/2026.html">Atlanta Hawks</a>'
    )
    participants = parse_participants(entry)
    assert [p["bref_slug"] for p in participants] == ["HOU", "ATL"]


@pytest.mark.unit
def test_player_named_inside_a_pick_clause_is_kept() -> None:
    """The pick is prose, but the player later selected is a real link."""
    entry = (
        'the <a data-attr-from="HOU" href="/teams/HOU/2026.html">Houston Rockets</a> '
        'traded a 2026 2nd round draft pick (<a href="/players/b/bilodty01.html">'
        "Tyler Bilodeau</a> was later selected) to the "
        '<a data-attr-to="BRK" href="/teams/BRK/2026.html">Brooklyn Nets</a>'
    )
    participants = parse_participants(entry)
    assert {p["bref_slug"] for p in participants} == {"HOU", "bilodty01", "BRK"}


@pytest.mark.unit
def test_unlinked_and_foreign_hrefs_are_ignored() -> None:
    entry = (
        'The <a data-attr-to="SAS" href="/teams/SAS/2026.html">San Antonio Spurs</a> '
        'signed a player from <a href="/international/euroleague/2026.html">EuroLeague</a>'
    )
    assert [p["bref_slug"] for p in parse_participants(entry)] == ["SAS"]


@pytest.mark.unit
def test_repeated_link_in_one_entry_is_deduped() -> None:
    entry = (
        '<a href="/players/k/keyty01.html">Tyreke Key</a> and '
        '<a href="/players/k/keyty01.html">Tyreke Key</a>'
    )
    assert len(parse_participants(entry)) == 1


@pytest.mark.unit
def test_parse_returns_empty_without_the_list() -> None:
    assert (
        parse_transactions_html("<html><body>no list</body></html>", season=SEASON, source_url="u")
        == []
    )


@pytest.mark.unit
def test_every_participant_has_a_usable_identity(parsed: list[dict]) -> None:
    for row in parsed:
        for participant in row["participants"]:
            assert participant["participant_type"] in {"player", "team"}
            assert participant["direction"] in {"from", "to", "none"}
            assert participant["bref_slug"]
            assert len(participant["bref_slug"]) <= 50
            assert 0 < len(participant["display_name"]) <= 200


@contextmanager
def _session(mock_session):
    yield mock_session


def _patch_scrape(monkeypatch: pytest.MonkeyPatch, *, known_player: bool = True):
    session = MagicMock()
    monkeypatch.setattr("scrapers.transactions.get_session", lambda: _session(session))
    monkeypatch.setattr("scrapers.transactions.seed_team_catalog", lambda *args, **kwargs: 30)
    monkeypatch.setattr(
        "scrapers.transactions.resolve_team_id", lambda _session, code: f"team-{code}"
    )
    monkeypatch.setattr(
        "scrapers.transactions.resolve_player_id",
        lambda _session, **kwargs: f"player-{kwargs['external_id']}" if known_player else None,
    )
    captured: list[list[dict]] = []

    def fake_upsert(_session, _model, rows, _conflict):
        captured.append(rows)
        return len(rows)

    monkeypatch.setattr("scrapers.transactions.upsert_rows", fake_upsert)
    return captured


@pytest.mark.unit
def test_scrape_transactions_writes_parents_then_children(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _patch_scrape(monkeypatch)
    n_transactions, n_participants = scrape_transactions(SEASON, fetch_html=lambda url: _html())
    assert n_transactions == 1130
    assert n_participants > 2000
    # Parents first: participants carry the FK back to transactions.
    transactions, participants = captured
    assert set(transactions[0]) == {
        "transaction_key",
        "transaction_date",
        "season",
        "description",
        "source_url",
        "scraped_at",
    }
    assert participants[0]["team_id"] == "team-MIN"
    assert participants[0]["player_id"] is None
    player_row = next(row for row in participants if row["participant_type"] == "player")
    assert player_row["player_id"] == "player-bernaju01"
    assert player_row["team_id"] is None


@pytest.mark.unit
def test_scrape_transactions_skips_unresolved_players(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unknown slug is a data gap, not a failed run."""
    captured = _patch_scrape(monkeypatch, known_player=False)
    n_transactions, n_participants = scrape_transactions(SEASON, fetch_html=lambda url: _html())
    assert n_transactions == 1130
    _, participants = captured
    assert participants
    assert {row["participant_type"] for row in participants} == {"team"}
    assert n_participants == len(participants)


@pytest.mark.unit
def test_scrape_transactions_requests_the_season_end_year(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_scrape(monkeypatch)
    seen: list[str] = []

    def fetch(url: str) -> str:
        seen.append(url)
        return _html()

    scrape_transactions("2025-26", fetch_html=fetch)
    assert seen == ["https://www.basketball-reference.com/leagues/NBA_2026_transactions.html"]


@pytest.mark.unit
def test_scrape_transactions_empty_page_is_not_an_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_scrape(monkeypatch)
    assert scrape_transactions(SEASON, fetch_html=lambda url: "<html></html>") == (0, 0)


@pytest.mark.unit
def test_cli_scrape_transactions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("main.scrape_transactions", lambda season: (12, 30))
    result = CliRunner().invoke(cli, ["scrape-transactions", "--season", "2025-26"])
    assert result.exit_code == 0
    assert "12" in result.output
    assert "30" in result.output
