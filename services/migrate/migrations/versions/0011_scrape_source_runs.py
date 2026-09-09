"""Add source.scrape_source_runs: one row per source per pipeline run.

Revision ID: 0011_scrape_source_runs
Revises: 0010_pbp_secondary_player
Create Date: 2026-09-09

source.pipeline_runs records one status for a whole sync, so a run where
injuries returned zero rows and odds 404'd is indistinguishable from a clean
one. execute_scrape already names every source via SyncAlert.try_run; this
table persists that per-step outcome so a failure can be attributed to a
source and retried on its own.

status is mechanical (did fetch+parse+write complete). expectation is the
separate verdict on whether the result looks sane, because "not published
yet" and "parse break" are indistinguishable within a single run and only
separable by how many consecutive runs come back below expectation.

Revision id is short on purpose: alembic_version.version_num is VARCHAR(32).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0011_scrape_source_runs"
down_revision: str | Sequence[str] | None = "0010_pbp_secondary_player"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE source.scrape_source_runs (
            id              SERIAL PRIMARY KEY,
            run_id          INTEGER NOT NULL
                            REFERENCES source.pipeline_runs(run_id) ON DELETE CASCADE,
            source_name     VARCHAR(64) NOT NULL,
            status          VARCHAR(20) NOT NULL,
            expectation     VARCHAR(20) NOT NULL DEFAULT 'not_checked',
            rows_written    INTEGER,
            season          VARCHAR(10),
            attempt         INTEGER NOT NULL DEFAULT 1,
            error_type      VARCHAR(100),
            error_detail    TEXT,
            started_at      TIMESTAMP NOT NULL DEFAULT NOW(),
            finished_at     TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX idx_scrape_source_runs_run ON source.scrape_source_runs (run_id)")
    # Drives the "latest status per source" and consecutive-below streak queries.
    op.execute(
        """
        CREATE INDEX idx_scrape_source_runs_source_started
            ON source.scrape_source_runs (source_name, started_at DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS source.scrape_source_runs")
