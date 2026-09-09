"""Persist model evaluation metrics by model, evaluation, and season."""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0013_model_evaluations"
down_revision: str | Sequence[str] | None = "0012_ml_v2_artifacts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE source.model_evaluations (
            model_name              VARCHAR(50) NOT NULL,
            model_version           VARCHAR(50) NOT NULL,
            evaluation_name         VARCHAR(64) NOT NULL,
            season                  VARCHAR(10) NOT NULL,
            evaluated_at            TIMESTAMP NOT NULL DEFAULT NOW(),
            n                       INTEGER NOT NULL CHECK (n >= 0),
            logloss                DOUBLE PRECISION,
            brier                  DOUBLE PRECISION,
            accuracy               DOUBLE PRECISION,
            home_always_accuracy   DOUBLE PRECISION,
            PRIMARY KEY (model_name, model_version, evaluation_name, season)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS source.model_evaluations")
