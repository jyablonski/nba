"""Add source.reddit_comments (PRAW comment ingest).

Revision ID: 0009_source_reddit_comments
Revises: 0008_drop_scrape_reddit
Create Date: 2026-09-06

Sibling of source.reddit_posts: one row per comment, associated by
post_reddit_id (the parent submission reddit_id). Not stuffed into
reddit_posts. Grain is comment reddit_id.

Revision id is short on purpose: alembic_version.version_num is VARCHAR(32).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0009_source_reddit_comments"
down_revision: str | Sequence[str] | None = "0008_drop_scrape_reddit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE source.reddit_comments (
            reddit_id       VARCHAR(16) PRIMARY KEY,
            post_reddit_id  VARCHAR(16) NOT NULL REFERENCES source.reddit_posts(reddit_id),
            parent_id       VARCHAR(20),
            author          VARCHAR(50),
            body            TEXT,
            score           INTEGER NOT NULL DEFAULT 0,
            created_utc     TIMESTAMP NOT NULL,
            permalink       VARCHAR(500) NOT NULL,
            scraped_at      TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_reddit_comments_post_reddit_id ON source.reddit_comments(post_reddit_id)"
    )
    op.execute(
        "CREATE INDEX idx_reddit_comments_created_utc ON source.reddit_comments(created_utc)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE source.reddit_comments")
