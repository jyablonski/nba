"""SQL against gold.fct_standings, with Regular Season game-result overlay."""

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

CONFERENCE_RANK_ORDER = f"""
    {RECORD_WIN_PCT} DESC NULLS LAST,
    {RECORD_WINS} DESC NULLS LAST,
    {RECORD_LOSSES} ASC NULLS LAST,
    dim_teams.team_name
"""

DERIVED_CONFERENCE_RANK = f"""
    coalesce(
        fct_standings.conference_rank,
        rank() OVER (
            PARTITION BY dim_teams.conference
            ORDER BY {CONFERENCE_RANK_ORDER}
        )
    )
"""

DERIVED_GAMES_BACK = f"""
    coalesce(
        fct_standings.games_back,
        CASE
            WHEN {RECORD_WINS} IS NULL OR {RECORD_LOSSES} IS NULL THEN NULL
            ELSE (
                (
                    first_value({RECORD_WINS}) OVER (
                        PARTITION BY dim_teams.conference
                        ORDER BY {CONFERENCE_RANK_ORDER}
                    ) - {RECORD_WINS}
                ) + (
                    {RECORD_LOSSES} - first_value({RECORD_LOSSES}) OVER (
                        PARTITION BY dim_teams.conference
                        ORDER BY {CONFERENCE_RANK_ORDER}
                    )
                )
            ) / 2.0
        END
    )
"""

REGULAR_SEASON_FORM = f"""
    WITH appearances AS (
        SELECT
            fct_team_game_results.home_team_id AS team_id,
            fct_team_game_results.winning_team_id,
            fct_team_game_results.game_date,
            fct_team_game_results.game_id
        FROM gold.fct_team_game_results
        WHERE
            fct_team_game_results.season_type = 'Regular Season'
            AND fct_team_game_results.season = ({RESOLVED_SEASON})
            AND fct_team_game_results.winning_team_id IS NOT NULL
        UNION ALL
        SELECT
            fct_team_game_results.away_team_id AS team_id,
            fct_team_game_results.winning_team_id,
            fct_team_game_results.game_date,
            fct_team_game_results.game_id
        FROM gold.fct_team_game_results
        WHERE
            fct_team_game_results.season_type = 'Regular Season'
            AND fct_team_game_results.season = ({RESOLVED_SEASON})
            AND fct_team_game_results.winning_team_id IS NOT NULL
    ),
    ordered AS (
        SELECT
            appearances.team_id,
            appearances.winning_team_id = appearances.team_id AS is_win,
            row_number() OVER (
                PARTITION BY appearances.team_id
                ORDER BY
                    appearances.game_date DESC,
                    appearances.game_id DESC
            ) AS game_number
        FROM appearances
    ),
    with_previous AS (
        SELECT
            ordered.*,
            lag(ordered.is_win) OVER (
                PARTITION BY ordered.team_id
                ORDER BY ordered.game_number
            ) AS previous_is_win
        FROM ordered
    ),
    marked AS (
        SELECT
            with_previous.*,
            sum(
                CASE
                    WHEN with_previous.game_number = 1
                        OR with_previous.is_win IS DISTINCT FROM with_previous.previous_is_win
                    THEN 1
                    ELSE 0
                END
            ) OVER (
                PARTITION BY with_previous.team_id
                ORDER BY with_previous.game_number
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS streak_group
        FROM with_previous
    ),
    last_ten AS (
        SELECT
            marked.team_id,
            count(*) FILTER (WHERE marked.game_number <= 10 AND marked.is_win) AS wins,
            count(*) FILTER (WHERE marked.game_number <= 10 AND NOT marked.is_win) AS losses
        FROM marked
        GROUP BY marked.team_id
    ),
    current_streak AS (
        SELECT
            marked.team_id,
            bool_or(marked.is_win) FILTER (WHERE marked.streak_group = 1) AS is_win,
            count(*) FILTER (WHERE marked.streak_group = 1) AS games
        FROM marked
        GROUP BY marked.team_id
    )
    SELECT
        last_ten.team_id,
        concat(
            CASE WHEN current_streak.is_win THEN 'W' ELSE 'L' END,
            current_streak.games
        ) AS streak,
        concat(last_ten.wins, '-', last_ten.losses) AS last_10
    FROM last_ten
    INNER JOIN current_streak
        ON current_streak.team_id = last_ten.team_id
"""

STANDINGS_BASE_FROM = f"""
    FROM gold.dim_teams
    LEFT JOIN gold.fct_standings
        ON fct_standings.team_id = dim_teams.team_id
        AND fct_standings.season = ({RESOLVED_SEASON})
        AND fct_standings.season_type = 'Regular Season'
        AND (:as_of IS NULL OR fct_standings.as_of_date = :as_of)
    LEFT JOIN ({REGULAR_SEASON_RECORDS}) AS records
        ON records.team_id = dim_teams.team_id
"""

STANDINGS_FILTER = """
    WHERE
        (fct_standings.team_id IS NOT NULL OR records.team_id IS NOT NULL)
        AND (:conference IS NULL OR upper(dim_teams.conference) = upper(:conference))
"""

STANDINGS_FROM = f"""
    {STANDINGS_BASE_FROM}
    LEFT JOIN ({REGULAR_SEASON_FORM}) AS form
        ON form.team_id = dim_teams.team_id
    {STANDINGS_FILTER}
"""

STANDINGS_COUNT_FROM = f"""
    {STANDINGS_BASE_FROM}
    {STANDINGS_FILTER}
"""

STANDINGS_SELECT = f"""
    dim_teams.team_id,
    dim_teams.abbreviation,
    dim_teams.team_name,
    ({RESOLVED_SEASON}) AS season,
    coalesce(fct_standings.season_type, 'Regular Season') AS season_type,
    fct_standings.as_of_date,
    dim_teams.conference,
    dim_teams.division,
    {DERIVED_CONFERENCE_RANK} AS conference_rank,
    fct_standings.division_rank,
    {RECORD_WINS} AS wins,
    {RECORD_LOSSES} AS losses,
    {RECORD_WIN_PCT} AS win_pct,
    {DERIVED_GAMES_BACK} AS games_back,
    fct_standings.conf_games_back,
    coalesce(nullif(nullif(btrim(fct_standings.streak), ''), '—'), form.streak) AS streak,
    coalesce(nullif(nullif(btrim(fct_standings.last_10), ''), '—'), form.last_10) AS last_10,
    {RECORD_SOURCE} AS record_source,
    fct_standings.playoff_seed
"""

LIST_STANDINGS_COUNT = text(
    f"""
    SELECT count(*) AS total
    {STANDINGS_COUNT_FROM}
    """
)

LIST_STANDINGS = text(
    f"""
    SELECT
        {STANDINGS_SELECT}
    {STANDINGS_FROM}
    ORDER BY
        dim_teams.conference,
        coalesce(fct_standings.playoff_seed, {DERIVED_CONFERENCE_RANK}) NULLS LAST,
        {RECORD_WIN_PCT} DESC NULLS LAST,
        dim_teams.team_name
    LIMIT :limit OFFSET :offset
    """
)

TEAM_STANDING = text(
    f"""
    SELECT *
    FROM (
        SELECT
            {STANDINGS_SELECT}
        {STANDINGS_FROM}
    ) AS ranked
    WHERE ranked.team_id = :team_id
    LIMIT 1
    """
)
