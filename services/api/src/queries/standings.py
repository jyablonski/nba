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

STANDINGS_FROM = f"""
    FROM gold.dim_teams t
    LEFT JOIN gold.fct_standings s
        ON s.team_id = t.team_id
       AND s.season = ({RESOLVED_SEASON})
       AND s.season_type = 'Regular Season'
       AND (:as_of IS NULL OR s.as_of_date = :as_of)
    LEFT JOIN ({REGULAR_SEASON_RECORDS}) AS records
        ON records.team_id = t.team_id
    WHERE (s.team_id IS NOT NULL OR records.team_id IS NOT NULL)
      AND (:conference IS NULL OR upper(t.conference) = upper(:conference))
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
    s.streak,
    s.last_10,
    {RECORD_SOURCE} AS record_source
"""

LIST_STANDINGS_COUNT = text(
    f"""
    SELECT count(*) AS total
    {STANDINGS_FROM}
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
