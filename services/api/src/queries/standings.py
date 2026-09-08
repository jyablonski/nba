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
    t.team_name
"""

DERIVED_CONFERENCE_RANK = f"""
    coalesce(
        s.conference_rank,
        rank() OVER (
            PARTITION BY t.conference
            ORDER BY {CONFERENCE_RANK_ORDER}
        )
    )
"""

DERIVED_GAMES_BACK = f"""
    coalesce(
        s.games_back,
        CASE
            WHEN {RECORD_WINS} IS NULL OR {RECORD_LOSSES} IS NULL THEN NULL
            ELSE (
                (
                    first_value({RECORD_WINS}) OVER (
                        PARTITION BY t.conference
                        ORDER BY {CONFERENCE_RANK_ORDER}
                    ) - {RECORD_WINS}
                ) + (
                    {RECORD_LOSSES} - first_value({RECORD_LOSSES}) OVER (
                        PARTITION BY t.conference
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
            games.home_team_id AS team_id,
            games.winning_team_id,
            games.game_date,
            games.game_id
        FROM gold.fct_team_game_results AS games
        WHERE games.season_type = 'Regular Season'
          AND games.season = ({RESOLVED_SEASON})
          AND games.winning_team_id IS NOT NULL
        UNION ALL
        SELECT
            games.away_team_id AS team_id,
            games.winning_team_id,
            games.game_date,
            games.game_id
        FROM gold.fct_team_game_results AS games
        WHERE games.season_type = 'Regular Season'
          AND games.season = ({RESOLVED_SEASON})
          AND games.winning_team_id IS NOT NULL
    ),
    ordered AS (
        SELECT
            appearances.team_id,
            appearances.winning_team_id = appearances.team_id AS is_win,
            row_number() OVER (
                PARTITION BY appearances.team_id
                ORDER BY appearances.game_date DESC, appearances.game_id DESC
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
    FROM gold.dim_teams t
    LEFT JOIN gold.fct_standings s
        ON s.team_id = t.team_id
       AND s.season = ({RESOLVED_SEASON})
       AND s.season_type = 'Regular Season'
       AND (:as_of IS NULL OR s.as_of_date = :as_of)
    LEFT JOIN ({REGULAR_SEASON_RECORDS}) AS records
        ON records.team_id = t.team_id
"""

STANDINGS_FILTER = """
    WHERE (s.team_id IS NOT NULL OR records.team_id IS NOT NULL)
      AND (:conference IS NULL OR upper(t.conference) = upper(:conference))
"""

STANDINGS_FROM = f"""
    {STANDINGS_BASE_FROM}
    LEFT JOIN ({REGULAR_SEASON_FORM}) AS form
        ON form.team_id = t.team_id
    {STANDINGS_FILTER}
"""

STANDINGS_COUNT_FROM = f"""
    {STANDINGS_BASE_FROM}
    {STANDINGS_FILTER}
"""

STANDINGS_SELECT = f"""
    t.team_id,
    t.abbreviation,
    t.team_name,
    ({RESOLVED_SEASON}) AS season,
    coalesce(s.season_type, 'Regular Season') AS season_type,
    s.as_of_date,
    t.conference,
    t.division,
    {DERIVED_CONFERENCE_RANK} AS conference_rank,
    s.division_rank,
    {RECORD_WINS} AS wins,
    {RECORD_LOSSES} AS losses,
    {RECORD_WIN_PCT} AS win_pct,
    {DERIVED_GAMES_BACK} AS games_back,
    s.conf_games_back,
    coalesce(nullif(nullif(btrim(s.streak), ''), '—'), form.streak) AS streak,
    coalesce(nullif(nullif(btrim(s.last_10), ''), '—'), form.last_10) AS last_10,
    {RECORD_SOURCE} AS record_source
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
        t.conference,
        conference_rank NULLS LAST,
        {RECORD_WIN_PCT} DESC NULLS LAST,
        t.team_name
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
