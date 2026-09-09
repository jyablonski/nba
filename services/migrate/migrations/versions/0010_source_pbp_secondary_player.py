"""Add source.play_by_play.secondary_player_id.

Revision ID: 0010_pbp_secondary_player
Revises: 0009_source_reddit_comments
Create Date: 2026-09-08

Basketball-Reference actions name two players on assisted shots, steals,
blocks, drawn fouls and substitutions. player_id is the primary actor
(scorer / turnover committer / fouler / player entering); this column holds
the other one so those events can be aggregated per player.

Revision id is short on purpose: alembic_version.version_num is VARCHAR(32).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0010_pbp_secondary_player"
down_revision: str | Sequence[str] | None = "0009_source_reddit_comments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE source.play_by_play
            ADD COLUMN IF NOT EXISTS secondary_player_id UUID
            REFERENCES source.players(player_id)
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE source.play_by_play DROP COLUMN IF EXISTS secondary_player_id")
