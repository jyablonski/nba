from contextlib import contextmanager
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from scrapers.player_game_logs import _ensure_reference_data, _player_ids_for_season


@contextmanager
def _session(mock_session):
    yield mock_session


@pytest.mark.unit
def test_player_ids_for_season_returns_uuid_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    player_ids = [uuid4(), uuid4()]
    session = MagicMock()
    session.query.return_value.filter.return_value.all.return_value = [
        (player_ids[0],),
        (player_ids[1],),
    ]
    monkeypatch.setattr("scrapers.player_game_logs.get_session", lambda: _session(session))
    assert _player_ids_for_season("2024-25", active_only=True) == player_ids


@pytest.mark.unit
def test_ensure_reference_data_calls_bref_bootstraps(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    session.query.return_value.first.return_value = None
    session.query.return_value.filter.return_value.first.return_value = None
    monkeypatch.setattr("scrapers.player_game_logs.get_session", lambda: _session(session))
    calls: list[str] = []
    monkeypatch.setattr("scrapers.teams.scrape_teams", lambda: calls.append("teams"))
    monkeypatch.setattr("scrapers.players.scrape_players", lambda season: calls.append("players"))
    monkeypatch.setattr("scrapers.games.scrape_games", lambda season: calls.append("games"))
    _ensure_reference_data("2024-25")
    assert calls == ["teams", "players", "games"]
