"""SQL against gold team dims and game results."""

from __future__ import annotations

from sqlalchemy import text

from queries.records import (
    RECORD_LOSSES,
    RECORD_SOURCE,
    RECORD_WIN_PCT,
    RECORD_WINS,
    REGULAR_SEASON_RECORDS,
    RESOLVED_SEASON,
)

TEAM_GAME_FILTERS = """
    (g.home_team_id = :team_id OR g.away_team_id = :team_id)
    AND (:season IS NULL OR g.season = :season)
    AND (:since_season IS NULL OR g.season >= :since_season)
    AND (
        :opponent_team_id IS NULL
        OR (
            (g.home_team_id = :team_id AND g.away_team_id = :opponent_team_id)
            OR (g.away_team_id = :team_id AND g.home_team_id = :opponent_team_id)
        )
    )
    AND (
        :location IS NULL
        OR (:location = 'home' AND g.home_team_id = :team_id)
        OR (:location = 'away' AND g.away_team_id = :team_id)
    )
    AND (:arena_city IS NULL OR g.arena_city ILIKE :arena_city)
    AND (:season_type IS NULL OR g.season_type = :season_type)
"""

TEAM_BY_ID = text(
    """
    SELECT
        team_id, abbreviation, team_name, conference, division, city, nickname,
        arena_name, arena_latitude, arena_longitude,
        primary_color, alternate_color,
        current_season_payroll, current_remaining_guaranteed,
        current_contract_season,
        salary_cap, luxury_tax, first_apron, second_apron,
        over_luxury_tax, over_first_apron, over_second_apron
    FROM gold.dim_teams
    WHERE team_id = :team_id
    """
)

TEAM_BY_ABBREVIATION = text(
    """
    SELECT
        team_id, abbreviation, team_name, conference, division, city, nickname,
        arena_name, arena_latitude, arena_longitude,
        primary_color, alternate_color,
        current_season_payroll, current_remaining_guaranteed,
        current_contract_season,
        salary_cap, luxury_tax, first_apron, second_apron,
        over_luxury_tax, over_first_apron, over_second_apron
    FROM gold.dim_teams
    WHERE upper(abbreviation) = upper(:abbreviation)
    """
)

LIST_TEAMS_COUNT = text("SELECT count(*) FROM gold.dim_teams")

# Regular Season points scored/allowed per game. Gold has no possessions or
# offensive rebounds, so this is not possession-adjusted ORtg/DRtg.
REGULAR_SEASON_SCORING = f"""
    SELECT
        appearances.team_id,
        round(avg(appearances.pts_scored)::numeric, 1) AS pts_scored_avg,
        round(avg(appearances.pts_allowed)::numeric, 1) AS pts_allowed_avg
    FROM (
        SELECT
            games.home_team_id AS team_id,
            games.home_score AS pts_scored,
            games.away_score AS pts_allowed
        FROM gold.fct_team_game_results AS games
        WHERE games.season_type = 'Regular Season'
          AND games.season = ({RESOLVED_SEASON})
          AND games.home_score IS NOT NULL
          AND games.away_score IS NOT NULL
        UNION ALL
        SELECT
            games.away_team_id AS team_id,
            games.away_score AS pts_scored,
            games.home_score AS pts_allowed
        FROM gold.fct_team_game_results AS games
        WHERE games.season_type = 'Regular Season'
          AND games.season = ({RESOLVED_SEASON})
          AND games.home_score IS NOT NULL
          AND games.away_score IS NOT NULL
    ) AS appearances
    GROUP BY appearances.team_id
"""

LIST_TEAMS = text(
    f"""
    SELECT
        t.team_id,
        t.abbreviation,
        t.team_name,
        t.conference,
        t.division,
        t.city,
        t.nickname,
        {RECORD_WINS} AS wins,
        {RECORD_LOSSES} AS losses,
        {RECORD_WIN_PCT} AS win_pct,
        {RECORD_SOURCE} AS record_source,
        scoring.pts_scored_avg,
        scoring.pts_allowed_avg
    FROM gold.dim_teams t
    LEFT JOIN gold.fct_standings s
        ON s.team_id = t.team_id
       AND s.season = ({RESOLVED_SEASON})
       AND s.season_type = 'Regular Season'
    LEFT JOIN ({REGULAR_SEASON_RECORDS}) AS records
        ON records.team_id = t.team_id
    LEFT JOIN ({REGULAR_SEASON_SCORING}) AS scoring
        ON scoring.team_id = t.team_id
    ORDER BY t.conference, t.division, t.team_name
    LIMIT :limit OFFSET :offset
    """
)

LATEST_SEASON_FOR_TEAM = text(
    """
    SELECT max(season) AS season
    FROM gold.fct_team_game_results
    WHERE home_team_id = :team_id OR away_team_id = :team_id
    """
)

COMPUTE_RECORD = text(
    f"""
    SELECT
        count(*) AS games,
        count(*) FILTER (WHERE g.winning_team_id = :team_id) AS wins
    FROM gold.fct_team_game_results g
    WHERE {TEAM_GAME_FILTERS}
    """
)

COMPUTE_RECORDS_BY_SEASON_TYPE = text(
    """
    SELECT
        g.season_type,
        count(*) AS games,
        count(*) FILTER (WHERE g.winning_team_id = :team_id) AS wins
    FROM gold.fct_team_game_results g
    WHERE (g.home_team_id = :team_id OR g.away_team_id = :team_id)
      AND g.season = :season
    GROUP BY g.season_type
    """
)

LIST_TEAM_GAMES_COUNT = text(
    f"""
    SELECT count(*) AS total
    FROM gold.fct_team_game_results g
    WHERE {TEAM_GAME_FILTERS}
    """
)

LIST_TEAM_GAMES = text(
    f"""
    SELECT
        g.game_id,
        g.season,
        g.season_type,
        g.game_date,
        coalesce(nullif(btrim(g.arena), ''), home_teams.arena_name) AS arena,
        coalesce(nullif(btrim(g.arena_city), ''), home_teams.city) AS arena_city,
        g.arena_state,
        g.home_team_id,
        g.home_team_abbreviation,
        g.home_team_name,
        g.home_score,
        g.away_team_id,
        g.away_team_abbreviation,
        g.away_team_name,
        g.away_score,
        g.winning_team_id,
        g.winner_location,
        CASE
            WHEN g.home_score IS NULL OR g.away_score IS NULL THEN NULL
            WHEN g.home_team_id = :team_id THEN g.home_score - g.away_score
            ELSE g.away_score - g.home_score
        END AS score_margin,
        CASE
            WHEN g.home_team_id = :team_id THEN 'home'
            ELSE 'away'
        END AS location,
        CASE
            WHEN g.home_team_id = :team_id THEN g.away_team_id
            ELSE g.home_team_id
        END AS opponent_team_id,
        CASE
            WHEN g.home_team_id = :team_id THEN g.away_team_abbreviation
            ELSE g.home_team_abbreviation
        END AS opponent_abbreviation,
        CASE
            WHEN g.home_team_id = :team_id THEN g.away_team_name
            ELSE g.home_team_name
        END AS opponent_name,
        CASE
            WHEN g.home_team_id = :team_id THEN g.home_score
            ELSE g.away_score
        END AS team_score,
        CASE
            WHEN g.home_team_id = :team_id THEN g.away_score
            ELSE g.home_score
        END AS opponent_score,
        (g.winning_team_id = :team_id) AS is_win
    FROM gold.fct_team_game_results g
    LEFT JOIN gold.dim_teams AS home_teams
        ON home_teams.team_id = g.home_team_id
    WHERE {TEAM_GAME_FILTERS}
    ORDER BY g.game_date DESC, g.game_id DESC
    LIMIT :limit OFFSET :offset
    """
)
