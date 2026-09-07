from contextlib import contextmanager
from datetime import date, datetime
from unittest.mock import MagicMock
from uuid import UUID, uuid5

import pytest
from click.testing import CliRunner

from elo import MODEL_VERSION, GameRow
from main import cli, main
from queries import (
    INSERT_GAME_PREDICTION,
    SELECT_MARKET_WP_BY_GAME,
    SELECT_REGULAR_SEASON_FINALS,
    SELECT_UPCOMING_GAMES,
)
from scoring import (
    build_prediction_rows,
    evaluate,
    evaluate_holdout,
    holdout_season,
    load_market_wp,
    load_regular_season_finals,
    load_upcoming_games,
    score_and_persist,
)

TEAM_HOME = UUID("00000000-0000-4000-8000-000000000201")
TEAM_AWAY = UUID("00000000-0000-4000-8000-000000000202")
GAME_NAMESPACE = UUID("00000000-0000-0000-0000-000000000001")


def _id(value: str) -> UUID:
    return uuid5(GAME_NAMESPACE, value)


@contextmanager
def _session(mock_session):
    yield mock_session


def _game(season: str, home_won: bool | None, game_id: str = "1") -> GameRow:
    return GameRow(
        game_id=_id(game_id),
        game_date=date(2024, 10, 22),
        season=season,
        home_team_id=TEAM_HOME,
        away_team_id=TEAM_AWAY,
        home_won=home_won,
    )


@pytest.mark.unit
def test_query_sql_targets_gold_and_source() -> None:
    assert "gold.fct_team_game_results" in str(SELECT_REGULAR_SEASON_FINALS)
    assert "Regular Season" in str(SELECT_REGULAR_SEASON_FINALS)
    assert "gold.fct_games_schedule" in str(SELECT_UPCOMING_GAMES)
    assert "silver.stg_game_odds" in str(SELECT_MARKET_WP_BY_GAME)
    assert "INSERT INTO source.game_predictions" in str(INSERT_GAME_PREDICTION)


@pytest.mark.unit
def test_holdout_season_and_evaluate() -> None:
    games = [
        _game("2023-24", True, "a"),
        _game("2023-24", False, "b"),
        _game("2024-25", True, "c"),
        _game("2024-25", True, "d"),
    ]
    assert holdout_season(games) == "2024-25"
    assert holdout_season(games[:1]) is None
    result = evaluate_holdout(games)
    assert result["holdout_season"] == "2024-25"
    assert result["n"] == 2
    assert result["model_version"] == MODEL_VERSION
    single = evaluate_holdout(games[:1])
    assert single["n"] == 1


@pytest.mark.unit
def test_build_prediction_rows_attaches_market_wp() -> None:
    upcoming = [_game("2024-25", None, "002")]
    rows = build_prediction_rows(
        upcoming,
        [0.61],
        {_id("002"): 0.55},
        as_of=datetime(2024, 10, 26, 12, 0, 0),
    )
    assert rows[0]["model_wp"] == 0.61
    assert rows[0]["market_wp"] == 0.55
    assert rows[0]["model_version"] == MODEL_VERSION


@pytest.mark.unit
def test_load_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    session.execute.return_value.mappings.return_value.all.return_value = [
        {
            "game_id": _id("002"),
            "game_date": date(2024, 10, 22),
            "season": "2024-25",
            "home_team_id": TEAM_HOME,
            "away_team_id": TEAM_AWAY,
            "winner_location": "home",
        }
    ]
    finals = load_regular_season_finals(session)
    assert finals[0].home_won is True
    session.execute.return_value.mappings.return_value.all.return_value = [
        {
            "game_id": _id("003"),
            "game_date": date(2024, 10, 27),
            "season": "2024-25",
            "home_team_id": TEAM_HOME,
            "away_team_id": TEAM_AWAY,
        }
    ]
    upcoming = load_upcoming_games(session)
    assert upcoming[0].home_won is None
    session.execute.return_value.mappings.return_value.all.return_value = [
        {"game_id": _id("003"), "market_wp": 0.58},
        {"game_id": _id("004"), "market_wp": None},
    ]
    assert load_market_wp(session) == {_id("003"): 0.58}


@pytest.mark.unit
def test_score_and_persist_and_evaluate(monkeypatch: pytest.MonkeyPatch) -> None:
    history = [_game("2023-24", True, "h1"), _game("2024-25", False, "h2")]
    upcoming = [_game("2024-25", None, "u1")]
    session = MagicMock()
    monkeypatch.setattr("scoring.get_session", lambda: _session(session))
    monkeypatch.setattr("scoring.load_regular_season_finals", lambda sess: history)
    monkeypatch.setattr("scoring.load_upcoming_games", lambda sess: upcoming)
    monkeypatch.setattr("scoring.load_market_wp", lambda sess: {_id("u1"): 0.52})
    monkeypatch.setattr("scoring.upsert_rows", lambda *args, **kwargs: 1)
    result = score_and_persist(as_of=datetime(2024, 10, 26, 8, 0, 0))
    assert result["written"] == 1
    assert result["upcoming_games"] == 1
    assert result["history_games"] == 2

    eval_result = evaluate()
    assert eval_result["n"] == 1


@pytest.mark.unit
def test_cli_eval_and_score(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "main.evaluate",
        lambda: {
            "model_name": "elo",
            "model_version": "elo-v0",
            "holdout_season": "2024-25",
            "n": 2,
            "logloss": 0.68,
            "brier": 0.24,
            "accuracy": 0.55,
            "home_always_accuracy": 0.58,
        },
    )
    monkeypatch.setattr(
        "main.score_and_persist",
        lambda: {
            "model_name": "elo",
            "model_version": "elo-v0",
            "history_games": 10,
            "upcoming_games": 3,
            "written": 3,
            "as_of": "2024-10-26T08:00:00",
        },
    )
    runner = CliRunner()
    ev = runner.invoke(cli, ["eval"])
    assert ev.exit_code == 0
    assert "logloss" in ev.output
    sc = runner.invoke(cli, ["score"])
    assert sc.exit_code == 0
    assert "written=3" in sc.output


@pytest.mark.unit
def test_main_invokes_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[bool] = []
    monkeypatch.setattr("main.cli", lambda: called.append(True))
    main()
    assert called == [True]


@pytest.mark.unit
def test_settings_and_db_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    from config import Settings
    from db import get_session, upsert_rows
    from models import GamePrediction

    settings = Settings(database_url="")
    assert settings.database_url.startswith("postgresql://")
    session = MagicMock()
    assert upsert_rows(session, GamePrediction, [], ["game_id"]) == 0
    session.execute.assert_not_called()
    now = datetime.now()
    rows = [
        {
            "game_id": "002",
            "as_of": now,
            "model_name": "elo",
            "model_version": "elo-v0",
            "home_team_id": 1,
            "away_team_id": 2,
            "model_wp": 0.6,
            "market_wp": None,
            "scraped_at": now,
        }
    ]
    assert upsert_rows(session, GamePrediction, rows, ["game_id", "as_of", "model_version"]) == 1
    session.execute.assert_called()

    fake = MagicMock()
    with monkeypatch.context() as ctx:
        ctx.setattr("db.SessionLocal", lambda: fake)
        with get_session() as db:
            assert db is fake
    fake.commit.assert_called()
    fake.close.assert_called()

    fake = MagicMock()
    fake.commit.side_effect = RuntimeError("fail")
    with monkeypatch.context() as ctx:
        ctx.setattr("db.SessionLocal", lambda: fake)
        with pytest.raises(RuntimeError):
            with get_session():
                pass
    fake.rollback.assert_called()
