"""Add source.transactions and source.transaction_participants.

Revision ID: 0017_transactions
Revises: 0016_reddit_author_flair
Create Date: 2026-09-12

Basketball-Reference's season transactions log. Two tables because a single
trade names several players and teams, so a flat row cannot hold it and cannot
join to the dimensions.

Team links carry the trade direction as data-attr-from / data-attr-to, so
`direction` is captured per participant. It is NOT NULL with a 'none' sentinel
for players rather than nullable: Postgres treats NULLs as distinct in a UNIQUE
constraint, so a nullable direction would let duplicate participant rows through
the very constraint meant to stop them.

`transaction_key` is sha256(transaction_date|description) rather than a unique
index on that pair directly: `description` is free prose in a TEXT column, and
a btree index entry over ~2704 bytes errors at insert time. The hash is
fixed-width, so the grain stays enforceable no matter how long an entry runs.

Known trade-off, accepted deliberately: if Basketball-Reference edits a
description's wording, the hash changes and the edit lands as a new row rather
than an update. The (transaction_date, description) pair stays queryable, so a
same-day reconcile can find those if it ever matters.

Revision id is short on purpose: alembic_version.version_num is VARCHAR(32).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0017_transactions"
down_revision: str | Sequence[str] | None = "0016_reddit_author_flair"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE source.transactions (
            id               SERIAL PRIMARY KEY,
            transaction_key  CHAR(64)     NOT NULL UNIQUE,
            transaction_date DATE         NOT NULL,
            season           VARCHAR(10)  NOT NULL,
            description      TEXT         NOT NULL,
            source_url       VARCHAR(300) NOT NULL,
            scraped_at       TIMESTAMP    NOT NULL DEFAULT now()
        )
        """
    )
    # Season + date is how every downstream model reads this table.
    op.execute(
        """
        CREATE INDEX transactions_season_date_idx
            ON source.transactions (season, transaction_date)
        """
    )
    op.execute(
        """
        CREATE TABLE source.transaction_participants (
            id               SERIAL PRIMARY KEY,
            transaction_key  CHAR(64)     NOT NULL
                REFERENCES source.transactions(transaction_key),
            participant_type VARCHAR(10)  NOT NULL,
            direction        VARCHAR(4)   NOT NULL DEFAULT 'none',
            bref_slug        VARCHAR(50)  NOT NULL,
            display_name     VARCHAR(200) NOT NULL,
            player_id        UUID REFERENCES source.players(player_id),
            team_id          UUID REFERENCES source.teams(team_id),
            scraped_at       TIMESTAMP    NOT NULL DEFAULT now(),
            CONSTRAINT transaction_participants_key_type_slug_key
                UNIQUE (transaction_key, participant_type, bref_slug, direction),
            CONSTRAINT transaction_participants_type_check
                CHECK (participant_type IN ('player', 'team')),
            CONSTRAINT transaction_participants_direction_check
                CHECK (direction IN ('from', 'to', 'none'))
        )
        """
    )
    op.execute(
        """
        CREATE INDEX transaction_participants_player_idx
            ON source.transaction_participants (player_id)
        """
    )
    op.execute(
        """
        CREATE INDEX transaction_participants_team_idx
            ON source.transaction_participants (team_id)
        """
    )


def downgrade() -> None:
    # Children first: participants hold the FK back to transactions.
    op.execute("DROP TABLE IF EXISTS source.transaction_participants")
    op.execute("DROP TABLE IF EXISTS source.transactions")
