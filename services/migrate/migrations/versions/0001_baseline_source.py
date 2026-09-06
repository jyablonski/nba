"""Baseline source schema (former raw ingest + ops pipeline tables).

Revision ID: 0001_baseline_source
Revises:
Create Date: 2026-09-03
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0001_baseline_source"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS source")

    op.execute(
        """
        CREATE TABLE source.players (
            player_id       INTEGER PRIMARY KEY,
            first_name      VARCHAR(100) NOT NULL,
            last_name       VARCHAR(100) NOT NULL,
            full_name       VARCHAR(200) NOT NULL,
            is_active       BOOLEAN NOT NULL DEFAULT FALSE,
            jersey_number   VARCHAR(10),
            position        VARCHAR(20),
            height          VARCHAR(10),
            weight          INTEGER,
            birth_date      DATE,
            team_id         INTEGER,
            from_year       INTEGER,
            to_year         INTEGER,
            scraped_at      TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE source.teams (
            team_id         INTEGER PRIMARY KEY,
            abbreviation    VARCHAR(5) NOT NULL,
            full_name       VARCHAR(100) NOT NULL,
            city            VARCHAR(50) NOT NULL,
            nickname        VARCHAR(50) NOT NULL,
            conference      VARCHAR(10) NOT NULL,
            division        VARCHAR(20) NOT NULL,
            scraped_at      TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE source.games (
            game_id         VARCHAR(20) PRIMARY KEY,
            season          VARCHAR(10) NOT NULL,
            season_type     VARCHAR(20) NOT NULL,
            game_date       DATE NOT NULL,
            home_team_id    INTEGER NOT NULL REFERENCES source.teams(team_id),
            away_team_id    INTEGER NOT NULL REFERENCES source.teams(team_id),
            home_score      INTEGER,
            away_score      INTEGER,
            arena           VARCHAR(100),
            city            VARCHAR(50),
            state           VARCHAR(50),
            status          VARCHAR(20) NOT NULL DEFAULT 'Final',
            scraped_at      TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX idx_games_date ON source.games(game_date)")
    op.execute("CREATE INDEX idx_games_season ON source.games(season)")
    op.execute("CREATE INDEX idx_games_home_team ON source.games(home_team_id)")
    op.execute("CREATE INDEX idx_games_away_team ON source.games(away_team_id)")

    op.execute(
        """
        CREATE TABLE source.player_game_logs (
            id              SERIAL PRIMARY KEY,
            player_id       INTEGER NOT NULL REFERENCES source.players(player_id),
            game_id         VARCHAR(20) NOT NULL REFERENCES source.games(game_id),
            team_id         INTEGER NOT NULL REFERENCES source.teams(team_id),
            game_date       DATE NOT NULL,
            season          VARCHAR(10) NOT NULL,
            matchup         VARCHAR(20) NOT NULL,
            wl              CHAR(1),
            min             REAL,
            pts             INTEGER,
            reb             INTEGER,
            ast             INTEGER,
            stl             INTEGER,
            blk             INTEGER,
            tov             INTEGER,
            fgm             INTEGER,
            fga             INTEGER,
            fg_pct          REAL,
            fg3m            INTEGER,
            fg3a            INTEGER,
            fg3_pct         REAL,
            ftm             INTEGER,
            fta             INTEGER,
            ft_pct          REAL,
            plus_minus      INTEGER,
            scraped_at      TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE (player_id, game_id)
        )
        """
    )
    op.execute("CREATE INDEX idx_pgl_player ON source.player_game_logs(player_id)")
    op.execute("CREATE INDEX idx_pgl_game ON source.player_game_logs(game_id)")
    op.execute("CREATE INDEX idx_pgl_date ON source.player_game_logs(game_date)")
    op.execute("CREATE INDEX idx_pgl_season ON source.player_game_logs(season)")

    op.execute(
        """
        CREATE TABLE source.player_contracts (
            id                      SERIAL PRIMARY KEY,
            bref_player_slug        VARCHAR(32) NOT NULL,
            player_name             VARCHAR(200) NOT NULL,
            player_name_normalized  VARCHAR(200) NOT NULL,
            bref_team_abbreviation  VARCHAR(5) NOT NULL,
            nba_team_abbreviation   VARCHAR(5) NOT NULL,
            season                  VARCHAR(10) NOT NULL,
            salary                  BIGINT,
            is_fully_guaranteed     BOOLEAN NOT NULL DEFAULT TRUE,
            remaining_guaranteed    BIGINT,
            player_age              INTEGER,
            source_url              VARCHAR(300) NOT NULL,
            scraped_at              TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE (bref_player_slug, bref_team_abbreviation, season)
        )
        """
    )
    op.execute("CREATE INDEX idx_player_contracts_season ON source.player_contracts(season)")
    op.execute(
        "CREATE INDEX idx_player_contracts_nba_team "
        "ON source.player_contracts(nba_team_abbreviation)"
    )

    op.execute(
        """
        CREATE TABLE source.team_payroll (
            id                      SERIAL PRIMARY KEY,
            bref_team_abbreviation  VARCHAR(5) NOT NULL,
            nba_team_abbreviation   VARCHAR(5) NOT NULL,
            season                  VARCHAR(10) NOT NULL,
            total_salary            BIGINT,
            remaining_guaranteed    BIGINT,
            source_url              VARCHAR(300) NOT NULL,
            scraped_at              TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE (bref_team_abbreviation, season)
        )
        """
    )
    op.execute("CREATE INDEX idx_team_payroll_season ON source.team_payroll(season)")
    op.execute(
        "CREATE INDEX idx_team_payroll_nba_team ON source.team_payroll(nba_team_abbreviation)"
    )

    op.execute(
        """
        CREATE TABLE source.scrape_pipeline (
            id                  INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
            enabled             BOOLEAN NOT NULL DEFAULT FALSE,
            season_active       BOOLEAN NOT NULL DEFAULT FALSE,
            season_start        DATE,
            season_end          DATE,
            scrape_mode         VARCHAR(32) NOT NULL DEFAULT 'daily',
            target_season       VARCHAR(10),
            last_success_at     TIMESTAMP,
            last_scrape_date    DATE,
            reason              TEXT,
            updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        INSERT INTO source.scrape_pipeline (id, enabled, season_active, scrape_mode, reason)
        VALUES (
            1,
            FALSE,
            FALSE,
            'daily',
            'Disabled by default (safe for off-season). Enable when the season is running.'
        )
        ON CONFLICT (id) DO NOTHING
        """
    )

    op.execute(
        """
        CREATE TABLE source.pipeline_runs (
            run_id          SERIAL PRIMARY KEY,
            triggered_by    VARCHAR(32) NOT NULL DEFAULT 'manual',
            status          VARCHAR(20) NOT NULL,
            scrape_action   VARCHAR(64),
            scrape_exit     INTEGER,
            dbt_exit        INTEGER,
            detail          TEXT,
            started_at      TIMESTAMP NOT NULL DEFAULT NOW(),
            finished_at     TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX idx_pipeline_runs_started ON source.pipeline_runs (started_at DESC)")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS source CASCADE")
