"""Shared Regular Season W–L from gold.fct_team_game_results."""

from __future__ import annotations

RESOLVED_SEASON = """
    coalesce(
        :season,
        (SELECT max(season) FROM gold.fct_standings),
        (
            SELECT max(season)
            FROM gold.fct_team_game_results
            WHERE season_type = 'Regular Season'
        )
    )
"""

REGULAR_SEASON_RECORDS = f"""
    SELECT
        appearances.team_id,
        count(*) AS games,
        count(*) FILTER (
            WHERE appearances.winning_team_id = appearances.team_id
        ) AS wins
    FROM (
        SELECT
            games.home_team_id AS team_id,
            games.winning_team_id
        FROM gold.fct_team_game_results AS games
        WHERE games.season_type = 'Regular Season'
          AND games.season = ({RESOLVED_SEASON})
        UNION ALL
        SELECT
            games.away_team_id AS team_id,
            games.winning_team_id
        FROM gold.fct_team_game_results AS games
        WHERE games.season_type = 'Regular Season'
          AND games.season = ({RESOLVED_SEASON})
    ) AS appearances
    GROUP BY appearances.team_id
"""

RECORD_WINS = "coalesce(s.wins, records.wins)"
RECORD_LOSSES = """
    coalesce(
        s.losses,
        CASE
            WHEN records.games IS NULL THEN NULL
            ELSE records.games - records.wins
        END
    )
"""
RECORD_WIN_PCT = """
    coalesce(
        s.win_pct,
        CASE
            WHEN records.games > 0
            THEN round(records.wins::numeric / records.games, 3)
            ELSE NULL
        END
    )
"""
RECORD_SOURCE = """
    CASE
        WHEN s.team_id IS NOT NULL THEN 'official'
        WHEN records.team_id IS NOT NULL THEN 'games'
        ELSE NULL
    END
"""
