"""Add author_flair to source.reddit_posts and source.reddit_comments.

Revision ID: 0016_reddit_author_flair
Revises: 0015_pipeline_refresh
Create Date: 2026-09-11

The existing `flair` column is the submission's own `link_flair_text` — a
content tag ("Highlight"), null on about nine r/nba posts in ten. The team badge
is the *author's* flair, a separate field, present on roughly half of posts and
two thirds of comments. It is what fct_reddit_flair resolves to a team.

Nullable with no backfill on purpose: Reddit returns the author's flair as it is
now, so rows already stored cannot be given a historical value. They fill in only
if that post is re-scraped, and old posts never are.

Revision id is short on purpose: alembic_version.version_num is VARCHAR(32).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0016_reddit_author_flair"
down_revision: str | Sequence[str] | None = "0015_pipeline_refresh"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE source.reddit_posts ADD COLUMN author_flair VARCHAR(200)")
    op.execute("ALTER TABLE source.reddit_comments ADD COLUMN author_flair VARCHAR(200)")


def downgrade() -> None:
    op.execute("ALTER TABLE source.reddit_comments DROP COLUMN author_flair")
    op.execute("ALTER TABLE source.reddit_posts DROP COLUMN author_flair")
