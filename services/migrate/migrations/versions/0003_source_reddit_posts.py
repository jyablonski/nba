"""Add source.reddit_posts (PRAW submission ingest).

Revision ID: 0003_source_reddit_posts
Revises: 0002_source_standings
Create Date: 2026-09-04
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003_source_reddit_posts"
down_revision: str | Sequence[str] | None = "0002_source_standings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE source.reddit_posts (
            reddit_id       VARCHAR(16) PRIMARY KEY,
            subreddit       VARCHAR(50) NOT NULL,
            title           TEXT NOT NULL,
            author          VARCHAR(50),
            score           INTEGER NOT NULL DEFAULT 0,
            num_comments    INTEGER NOT NULL DEFAULT 0,
            created_utc     TIMESTAMP NOT NULL,
            permalink       VARCHAR(500) NOT NULL,
            url             TEXT,
            selftext        TEXT,
            flair           VARCHAR(200),
            is_self         BOOLEAN NOT NULL DEFAULT FALSE,
            scraped_at      TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX idx_reddit_posts_subreddit ON source.reddit_posts(subreddit)")
    op.execute("CREATE INDEX idx_reddit_posts_created_utc ON source.reddit_posts(created_utc)")


def downgrade() -> None:
    op.execute("DROP TABLE source.reddit_posts")
