from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from db import get_session
from scrapers.games import _league_game_finder
from scrapers.player_game_logs import _ensure_reference_data, _player_ids_for_season


@contextmanager
def _session(mock_session):
    yield mock_session


@pytest.mark.unit
def test_get_session_rollback_on_body_error() -> None:
    session = MagicMock()
    with patch("db.SessionLocal", return_value=session), pytest.raises(RuntimeError):
        with get_session():
            raise RuntimeError("fail")
    session.rollback.assert_called_once()


@pytest.mark.unit
def test_league_game_finder(monkeypatch: pytest.MonkeyPatch) -> None:
    class Endpoint:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def get_normalized_dict(self):
            return {"LeagueGameFinderResults": [{"GAME_ID": "002"}]}

    monkeypatch.setattr("scrapers.games.nba_call", lambda fn: fn())

    import nba_api.stats.endpoints.leaguegamefinder as leaguegamefinder

    monkeypatch.setattr(leaguegamefinder, "LeagueGameFinder", Endpoint)
    rows = _league_game_finder(
        season="2024-25",
        season_type="Regular Season",
        date_from=date(2024, 10, 22),
        date_to=date(2024, 10, 22),
    )
    assert rows[0]["GAME_ID"] == "002"


@pytest.mark.unit
def test_player_ids_for_season(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    session.query.return_value.filter.return_value.all.return_value = [(1,), (2,)]
    monkeypatch.setattr("scrapers.player_game_logs.get_session", lambda: _session(session))
    ids = _player_ids_for_season("2024-25", active_only=True)
    assert ids == [1, 2]


@pytest.mark.unit
def test_ensure_reference_data(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    session.query.return_value.scalar.return_value = 1
    session.query.return_value.filter.return_value.scalar.return_value = 1
    monkeypatch.setattr("scrapers.player_game_logs.get_session", lambda: _session(session))
    _ensure_reference_data("2024-25")
