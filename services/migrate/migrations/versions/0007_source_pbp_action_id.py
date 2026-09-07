"""Widen source.play_by_play unique key to include action_id.

Revision ID: 0007_source_pbp_action_id
Revises: 0006_source_pipeline_reddit
Create Date: 2026-09-05

Basketball-Reference action rows already use the provider-independent
(game_id, action_number, action_id) grain in the clean baseline.

Revision id is short on purpose: alembic_version.version_num is VARCHAR(32).
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0007_source_pbp_action_id"
down_revision: str | Sequence[str] | None = "0006_source_pipeline_reddit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
