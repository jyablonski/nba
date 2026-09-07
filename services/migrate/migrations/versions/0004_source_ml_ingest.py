"""Add source tables for pregame ML ingest (injuries, odds, predictions).

Revision ID: 0004_source_ml_ingest
Revises: 0003_source_reddit_posts
Create Date: 2026-09-04

player_injuries is a current Basketball-Reference snapshot (not a historical
ledger). History exists only from the day scraping starts.

game_odds is a current The Odds API upcoming-slate snapshot. Historical
odds backfill is out of scope.

game_predictions is written by services/ml and copied to gold by dbt.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004_source_ml_ingest"
down_revision: str | Sequence[str] | None = "0003_source_reddit_posts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE source.player_injuries (
            id                      SERIAL PRIMARY KEY,
            player_id               UUID NOT NULL REFERENCES source.players(player_id),
            team_id                 UUID NOT NULL REFERENCES source.teams(team_id),
            player_name             VARCHAR(200) NOT NULL,
            player_name_normalized  VARCHAR(200) NOT NULL,
            update_date             DATE,
            description             TEXT NOT NULL,
            source_url              VARCHAR(300) NOT NULL,
            scraped_at              TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE (player_id, team_id)
        )
        """
    )
    op.execute("CREATE INDEX idx_player_injuries_team ON source.player_injuries(team_id)")
    op.execute("CREATE INDEX idx_player_injuries_scraped_at ON source.player_injuries(scraped_at)")

    op.execute(
        """
        CREATE TABLE source.game_odds (
            id                  SERIAL PRIMARY KEY,
            odds_event_id       VARCHAR(64) NOT NULL,
            commence_time       TIMESTAMP NOT NULL,
            home_team_name      VARCHAR(100) NOT NULL,
            away_team_name      VARCHAR(100) NOT NULL,
            game_id             UUID REFERENCES source.games(game_id),
            bookmaker           VARCHAR(50) NOT NULL,
            market              VARCHAR(20) NOT NULL,
            home_price          INTEGER,
            away_price          INTEGER,
            home_implied_wp     REAL,
            away_implied_wp     REAL,
            home_market_wp      REAL,
            away_market_wp      REAL,
            spread_home         REAL,
            scraped_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE (odds_event_id, bookmaker, market)
        )
        """
    )
    op.execute("CREATE INDEX idx_game_odds_commence ON source.game_odds(commence_time)")
    op.execute("CREATE INDEX idx_game_odds_game_id ON source.game_odds(game_id)")

    op.execute(
        """
        CREATE TABLE source.game_predictions (
            id              SERIAL PRIMARY KEY,
            game_id         UUID NOT NULL REFERENCES source.games(game_id),
            as_of           TIMESTAMP NOT NULL,
            model_name      VARCHAR(50) NOT NULL,
            model_version   VARCHAR(50) NOT NULL,
            home_team_id    UUID NOT NULL REFERENCES source.teams(team_id),
            away_team_id    UUID NOT NULL REFERENCES source.teams(team_id),
            model_wp        REAL NOT NULL,
            market_wp       REAL,
            scraped_at      TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE (game_id, as_of, model_version),
            CHECK (model_wp > 0 AND model_wp < 1)
        )
        """
    )
    op.execute("CREATE INDEX idx_game_predictions_game_id ON source.game_predictions(game_id)")
    op.execute("CREATE INDEX idx_game_predictions_as_of ON source.game_predictions(as_of)")


def downgrade() -> None:
    op.execute("DROP TABLE source.game_predictions")
    op.execute("DROP TABLE source.game_odds")
    op.execute("DROP TABLE source.player_injuries")
