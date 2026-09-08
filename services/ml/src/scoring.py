"""Fit Elo on Regular Season Finals and persist pregame predictions."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from db import get_session, upsert_rows
from elo import (
    MODEL_NAME,
    MODEL_VERSION,
    GameRow,
    fit_ratings,
    game_row_from_mapping,
    score_games,
    walk_forward,
)
from metrics import summarize
from models import GamePrediction
from queries.games import SELECT_REGULAR_SEASON_FINALS, SELECT_UPCOMING_GAMES
from queries.odds import SELECT_MARKET_WP_BY_GAME


def load_regular_season_finals(session: Session) -> list[GameRow]:
    rows = session.execute(SELECT_REGULAR_SEASON_FINALS).mappings().all()
    return [game_row_from_mapping(row) for row in rows]


def load_upcoming_games(session: Session) -> list[GameRow]:
    rows = session.execute(SELECT_UPCOMING_GAMES).mappings().all()
    return [game_row_from_mapping(row) for row in rows]


def load_market_wp(session: Session) -> dict[UUID, float]:
    rows = session.execute(SELECT_MARKET_WP_BY_GAME).mappings().all()
    market: dict[UUID, float] = {}
    for row in rows:
        game_id = UUID(str(row["game_id"]))
        value = row["market_wp"]
        if value is None:
            continue
        market[game_id] = float(value)
    return market


def holdout_season(games: list[GameRow]) -> str | None:
    seasons = sorted({game.season for game in games})
    if len(seasons) < 2:
        return None
    return seasons[-1]


def evaluate_holdout(games: list[GameRow]) -> dict[str, Any]:
    """Walk-forward Elo; report metrics on the latest Regular Season."""
    season = holdout_season(games)
    preds, _ratings = walk_forward(games, update=True)
    labels: list[int] = []
    holdout_preds: list[float] = []
    for game, pred in zip(games, preds, strict=True):
        if game.home_won is None:
            continue
        if season is not None and game.season != season:
            continue
        if season is None:
            labels.append(1 if game.home_won else 0)
            holdout_preds.append(pred)
            continue
        labels.append(1 if game.home_won else 0)
        holdout_preds.append(pred)
    metrics = summarize(labels, holdout_preds)
    return {
        "holdout_season": season or (games[-1].season if games else None),
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        **metrics,
    }


def build_prediction_rows(
    upcoming: list[GameRow],
    probs: list[float],
    market_wp: dict[UUID, float],
    *,
    as_of: datetime,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for game, prob in zip(upcoming, probs, strict=True):
        rows.append(
            {
                "game_id": game.game_id,
                "as_of": as_of,
                "model_name": MODEL_NAME,
                "model_version": MODEL_VERSION,
                "home_team_id": game.home_team_id,
                "away_team_id": game.away_team_id,
                "model_wp": float(prob),
                "market_wp": market_wp.get(game.game_id),
                "scraped_at": as_of,
            }
        )
    return rows


def score_and_persist(*, as_of: datetime | None = None) -> dict[str, Any]:
    scored_at = as_of or datetime.now()
    with get_session() as session:
        history = load_regular_season_finals(session)
        upcoming = load_upcoming_games(session)
        market = load_market_wp(session)
        ratings = fit_ratings(history)
        probs = score_games(upcoming, ratings)
        rows = build_prediction_rows(upcoming, probs, market, as_of=scored_at)
        written = upsert_rows(
            session,
            GamePrediction,
            rows,
            ["game_id", "as_of", "model_version"],
        )
    return {
        "history_games": len(history),
        "upcoming_games": len(upcoming),
        "written": written,
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "as_of": scored_at.isoformat(),
    }


def evaluate() -> dict[str, Any]:
    with get_session() as session:
        history = load_regular_season_finals(session)
    return evaluate_holdout(history)
