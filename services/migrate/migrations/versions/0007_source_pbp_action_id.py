"""Widen source.play_by_play unique key to include action_id.

Revision ID: 0007_source_pbp_action_id
Revises: 0006_source_pipeline_reddit
Create Date: 2026-09-05

PlayByPlayV3 repeats actionNumber for paired events (turnover+steal,
missed shot+block) with distinct actionId values. Grain is
(game_id, action_number, action_id).

Revision id is short on purpose: alembic_version.version_num is VARCHAR(32).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0007_source_pbp_action_id"
down_revision: str | Sequence[str] | None = "0006_source_pipeline_reddit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE source.play_by_play
           SET action_id = action_number
         WHERE action_id IS NULL
        """
    )
    op.execute(
        """
        ALTER TABLE source.play_by_play
            DROP CONSTRAINT play_by_play_game_id_action_number_key
        """
    )
    op.execute(
        """
        ALTER TABLE source.play_by_play
            ADD CONSTRAINT play_by_play_game_id_action_number_action_id_key
            UNIQUE (game_id, action_number, action_id)
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE source.play_by_play
            DROP CONSTRAINT play_by_play_game_id_action_number_action_id_key
        """
    )
    op.execute(
        """
        ALTER TABLE source.play_by_play
            ADD CONSTRAINT play_by_play_game_id_action_number_key
            UNIQUE (game_id, action_number)
        """
    )
