"""Add source tables for ML v2 artifacts and injury history.

Revision ID: 0012_ml_v2_artifacts
Revises: 0011_scrape_source_runs
Create Date: 2026-09-09

The injury history is append-only by player/team/day. The current injury
snapshot remains the operational table used by the product.

Model artifacts are deliberately small JSON documents so scoring does not
depend on a mounted filesystem or a rebuilt image.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0012_ml_v2_artifacts"
down_revision: str | Sequence[str] | None = "0011_scrape_source_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE source.player_injuries_history (
            id                      SERIAL PRIMARY KEY,
            player_id               UUID NOT NULL REFERENCES source.players(player_id),
            team_id                 UUID NOT NULL REFERENCES source.teams(team_id),
            player_name             VARCHAR(200) NOT NULL,
            player_name_normalized  VARCHAR(200) NOT NULL,
            update_date             DATE,
            description             TEXT NOT NULL,
            source_url              VARCHAR(300) NOT NULL,
            snapshot_date           DATE NOT NULL,
            scraped_at              TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE (player_id, team_id, snapshot_date)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_player_injuries_history_snapshot "
        "ON source.player_injuries_history(snapshot_date)"
    )
    op.execute(
        """
        CREATE TABLE source.model_artifacts (
            model_version   VARCHAR(50) PRIMARY KEY,
            model_name      VARCHAR(50) NOT NULL,
            artifact        JSONB NOT NULL,
            trained_at      TIMESTAMP NOT NULL,
            is_champion     BOOLEAN NOT NULL DEFAULT FALSE
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX model_artifacts_one_champion
            ON source.model_artifacts (is_champion)
            WHERE is_champion
        """
    )
    op.execute(
        """
        INSERT INTO source.model_artifacts
            (model_version, model_name, artifact, trained_at, is_champion)
        VALUES ('elo-v0', 'elo', '{}'::jsonb, NOW(), TRUE)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS source.model_artifacts")
    op.execute("DROP TABLE IF EXISTS source.player_injuries_history")
