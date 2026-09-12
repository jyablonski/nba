"""Shared Regular Season W–L from gold.fct_team_game_results."""

from __future__ import annotations

RESOLVED_SEASON = """
    coalesce(
        :season,
        (
            SELECT max(season)
            FROM gold.fct_standings
        ),
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
            fct_team_game_results.home_team_id AS team_id,
            fct_team_game_results.winning_team_id
        FROM gold.fct_team_game_results
        WHERE
            fct_team_game_results.season_type = 'Regular Season'
            AND fct_team_game_results.season = ({RESOLVED_SEASON})
        UNION ALL
        SELECT
            fct_team_game_results.away_team_id AS team_id,
            fct_team_game_results.winning_team_id
        FROM gold.fct_team_game_results
        WHERE
            fct_team_game_results.season_type = 'Regular Season'
            AND fct_team_game_results.season = ({RESOLVED_SEASON})
    ) AS appearances
    GROUP BY appearances.team_id
"""

RECORD_WINS = "coalesce(fct_standings.wins, records.wins)"
RECORD_LOSSES = """
    coalesce(
        fct_standings.losses,
        CASE
            WHEN records.games IS NULL THEN NULL
            ELSE records.games - records.wins
        END
    )
"""
RECORD_WIN_PCT = """
    coalesce(
        fct_standings.win_pct,
        CASE
            WHEN records.games > 0
            THEN round(records.wins::numeric / records.games, 3)
            ELSE NULL
        END
    )
"""
RECORD_SOURCE = """
    CASE
        WHEN fct_standings.team_id IS NOT NULL THEN 'official'
        WHEN records.team_id IS NOT NULL THEN 'games'
        ELSE NULL
    END
"""
