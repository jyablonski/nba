"""Add source.standings (season-to-date league standings).

Revision ID: 0002_source_standings
Revises: 0001_baseline_source
Create Date: 2026-09-04
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_source_standings"
down_revision: str | Sequence[str] | None = "0001_baseline_source"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE source.standings (
            id                  SERIAL PRIMARY KEY,
            team_id             INTEGER NOT NULL REFERENCES source.teams(team_id),
            season              VARCHAR(10) NOT NULL,
            season_type         VARCHAR(20) NOT NULL DEFAULT 'Regular Season',
            as_of_date          DATE NOT NULL,
            conference          VARCHAR(10),
            division            VARCHAR(20),
            conference_rank     INTEGER,
            division_rank       INTEGER,
            wins                INTEGER,
            losses              INTEGER,
            win_pct             REAL,
            games_back          REAL,
            conf_games_back     REAL,
            streak              VARCHAR(20),
            last_10             VARCHAR(10),
            scraped_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE (season, season_type, team_id)
        )
        """
    )
    op.execute("CREATE INDEX idx_standings_season ON source.standings(season)")
    op.execute("CREATE INDEX idx_standings_team_id ON source.standings(team_id)")
    op.execute("CREATE INDEX idx_standings_conference ON source.standings(conference)")


def downgrade() -> None:
    op.execute("DROP TABLE source.standings")
