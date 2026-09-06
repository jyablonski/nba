"""Drop scrape_reddit; r/nba always runs when the pipeline is enabled.

Revision ID: 0008_drop_scrape_reddit
Revises: 0007_source_pbp_action_id
Create Date: 2026-09-06

source.scrape_pipeline.season_active (plus the optional date window) gates
NBA daily ingest. Reddit is no longer a separate flag: enabled (or --force)
always attempts r/nba. pipeline_runs.reddit_ran / reddit_exit stay.

Revision id is short on purpose: alembic_version.version_num is VARCHAR(32).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0008_drop_scrape_reddit"
down_revision: str | Sequence[str] | None = "0007_source_pbp_action_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE source.scrape_pipeline DROP COLUMN IF EXISTS scrape_reddit")


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE source.scrape_pipeline
            ADD COLUMN IF NOT EXISTS scrape_reddit BOOLEAN NOT NULL DEFAULT FALSE
        """
    )
