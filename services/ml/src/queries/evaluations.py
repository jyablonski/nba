"""SQL for persisted walk-forward evaluation metrics."""

from __future__ import annotations

from sqlalchemy import text

UPSERT_MODEL_EVALUATION = text(
    """
    INSERT INTO source.model_evaluations (
        model_name,
        model_version,
        evaluation_name,
        season,
        evaluated_at,
        n,
        logloss,
        brier,
        accuracy,
        home_always_accuracy
    )
    VALUES (
        :model_name,
        :model_version,
        :evaluation_name,
        :season,
        :evaluated_at,
        :n,
        :logloss,
        :brier,
        :accuracy,
        :home_always_accuracy
    )
    ON CONFLICT (model_name, model_version, evaluation_name, season) DO UPDATE SET
        evaluated_at = EXCLUDED.evaluated_at,
        n = EXCLUDED.n,
        logloss = EXCLUDED.logloss,
        brier = EXCLUDED.brier,
        accuracy = EXCLUDED.accuracy,
        home_always_accuracy = EXCLUDED.home_always_accuracy
    """
)
