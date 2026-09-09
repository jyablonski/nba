"""Add source.admin_jobs: operator-requested job queue for the /admin console.

Revision ID: 0014_admin_jobs
Revises: 0013_model_evaluations
Create Date: 2026-09-09

The API cannot execute jobs itself: it runs in a container with no Docker
socket, and giving a publicly reachable FastAPI process docker.sock would be
root-equivalent on the host. So the admin console enqueues here and a host-side
runner claims and executes. The database stays the only thing the API touches,
and the table doubles as an audit log of who asked for what.

status transitions: queued -> running -> succeeded | failed. A job is claimed
with FOR UPDATE SKIP LOCKED so two runners can never take the same row.

Revision id is short on purpose: alembic_version.version_num is VARCHAR(32).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0014_admin_jobs"
down_revision: str | Sequence[str] | None = "0013_model_evaluations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE source.admin_jobs (
            job_id          SERIAL PRIMARY KEY,
            job_type        VARCHAR(32) NOT NULL,
            status          VARCHAR(20) NOT NULL DEFAULT 'queued',
            requested_by    VARCHAR(100) NOT NULL,
            exit_code       INTEGER,
            detail          TEXT,
            log_tail        TEXT,
            requested_at    TIMESTAMP NOT NULL DEFAULT NOW(),
            started_at      TIMESTAMP,
            finished_at     TIMESTAMP,
            CONSTRAINT admin_jobs_job_type_check
                CHECK (job_type IN ('scrape', 'dbt', 'ml', 'refresh')),
            CONSTRAINT admin_jobs_status_check
                CHECK (status IN ('queued', 'running', 'succeeded', 'failed'))
        )
        """
    )
    op.execute("CREATE INDEX idx_admin_jobs_requested ON source.admin_jobs (requested_at DESC)")
    # Partial unique index: at most one un-finished job at a time. The console
    # cannot queue a second refresh while one is pending, which is the cheap
    # half of the concurrency story (the runner's flock is the other half).
    op.execute(
        """
        CREATE UNIQUE INDEX admin_jobs_single_pending
            ON source.admin_jobs ((status IN ('queued', 'running')))
            WHERE status IN ('queued', 'running')
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS source.admin_jobs")
