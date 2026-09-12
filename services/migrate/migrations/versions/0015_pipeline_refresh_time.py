"""Add source.scrape_pipeline.daily_refresh_utc: when the host cron next runs.

Revision ID: 0015_pipeline_refresh_time
Revises: 0014_admin_jobs
Create Date: 2026-09-11

The refresh schedule lives in the host crontab, which the API cannot read. This
column is the one place an operator writes it down so `GET /api/v1/status` can
say when the next batch lands instead of the UI hardcoding a time. It is
maintained by hand: nothing writes it, and changing the crontab does not change
it. Null means "unknown", and the API returns a null next_scrape_at rather than
guessing — an unset column must not become a wrong promise in the UI.

TIME, not a cron expression: the host cron is daily, so a time of day is the
whole schedule and needs no cron parser in the API. A non-daily schedule would
need a different column and an expression evaluator.

Revision id is short on purpose: alembic_version.version_num is VARCHAR(32).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0015_pipeline_refresh"
down_revision: str | Sequence[str] | None = "0014_admin_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE source.scrape_pipeline ADD COLUMN daily_refresh_utc TIME")


def downgrade() -> None:
    op.execute("ALTER TABLE source.scrape_pipeline DROP COLUMN daily_refresh_utc")
