"""Add scrape_reddit gate and pipeline_runs reddit columns.

Revision ID: 0006_source_pipeline_reddit
Revises: 0005_source_play_by_play
Create Date: 2026-09-05

source.scrape_pipeline.scrape_reddit is the everyday r/nba switch (default
false). It is independent of season_active. pipeline_runs records whether
reddit ran and its exit.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0006_source_pipeline_reddit"
down_revision: str | Sequence[str] | None = "0005_source_play_by_play"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE source.scrape_pipeline
            ADD COLUMN IF NOT EXISTS scrape_reddit BOOLEAN NOT NULL DEFAULT FALSE
        """
    )
    op.execute(
        """
        ALTER TABLE source.pipeline_runs
            ADD COLUMN IF NOT EXISTS reddit_ran BOOLEAN NOT NULL DEFAULT FALSE
        """
    )
    op.execute(
        """
        ALTER TABLE source.pipeline_runs
            ADD COLUMN IF NOT EXISTS reddit_exit INTEGER
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE source.pipeline_runs DROP COLUMN IF EXISTS reddit_exit")
    op.execute("ALTER TABLE source.pipeline_runs DROP COLUMN IF EXISTS reddit_ran")
    op.execute("ALTER TABLE source.scrape_pipeline DROP COLUMN IF EXISTS scrape_reddit")
