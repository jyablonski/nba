"""Add source.play_by_play (provider-neutral event ingest).

Revision ID: 0005_source_play_by_play
Revises: 0004_source_ml_ingest
Create Date: 2026-09-05

Grain is one row per Basketball-Reference action for a game (unique on game_id + action_number + action_id).
Opt-in scrape only; not on scrape-all / scrape-daily / pipeline.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005_source_play_by_play"
down_revision: str | Sequence[str] | None = "0004_source_ml_ingest"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE source.play_by_play (
            id              SERIAL PRIMARY KEY,
            game_id         UUID NOT NULL REFERENCES source.games(game_id),
            season          VARCHAR(10) NOT NULL,
            action_number   INTEGER NOT NULL,
            action_id       INTEGER,
            period          INTEGER,
            clock           VARCHAR(32),
            score_home      INTEGER,
            score_away      INTEGER,
            team_id         UUID REFERENCES source.teams(team_id),
            player_id       UUID REFERENCES source.players(player_id),
            action_type     VARCHAR(50),
            sub_type        VARCHAR(80),
            description     TEXT,
            extras          JSONB,
            scraped_at      TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE (game_id, action_number, action_id)
        )
        """
    )
    op.execute("CREATE INDEX idx_play_by_play_season ON source.play_by_play(season)")
    op.execute("CREATE INDEX idx_play_by_play_player_id ON source.play_by_play(player_id)")


def downgrade() -> None:
    op.execute("DROP TABLE source.play_by_play")
