"""SQL for the public warehouse watermark and coverage counts."""

from sqlalchemy import text

WAREHOUSE_STATUS = text(
    """
    WITH seasons AS (
        SELECT season
        FROM gold.fct_team_game_results
        UNION
        SELECT season
        FROM gold.fct_player_game_logs
    ),
    pipeline_stamp AS (
        SELECT
            last_success_at,
            daily_refresh_utc
        FROM source.scrape_pipeline
        WHERE id = 1
    ),
    -- Next occurrence of the hand-maintained daily time, computed in the
    -- database so the answer cannot drift from the API container's clock.
    -- Null column stays null: an unset schedule is not a promise.
    next_refresh AS (
        SELECT
            CASE
                WHEN pipeline_stamp.daily_refresh_utc IS NULL THEN NULL
                WHEN (now() AT TIME ZONE 'utc')::time < pipeline_stamp.daily_refresh_utc
                    THEN (now() AT TIME ZONE 'utc')::date + pipeline_stamp.daily_refresh_utc
                ELSE (now() AT TIME ZONE 'utc')::date + 1 + pipeline_stamp.daily_refresh_utc
            END AS next_scrape_at
        FROM pipeline_stamp
    ),
    source_watermarks AS (
        SELECT max(scraped_at) AS scraped_at
        FROM source.games
        UNION ALL
        SELECT max(scraped_at)
        FROM source.player_game_logs
        UNION ALL
        SELECT max(scraped_at)
        FROM source.teams
        UNION ALL
        SELECT max(scraped_at)
        FROM source.players
        UNION ALL
        SELECT max(scraped_at)
        FROM source.standings
        UNION ALL
        SELECT max(scraped_at)
        FROM source.player_contracts
        UNION ALL
        SELECT max(scraped_at)
        FROM source.team_payroll
    ),
    source_stamp AS (
        SELECT max(source_watermarks.scraped_at) AS scraped_at
        FROM source_watermarks
    )
    SELECT
        coalesce(
            (SELECT last_success_at FROM pipeline_stamp),
            (SELECT scraped_at FROM source_stamp)
        ) AS last_scraped_at,
        (SELECT next_scrape_at FROM next_refresh) AS next_scrape_at,
        (SELECT count(*) FROM gold.dim_players) AS player_count,
        (SELECT count(*) FROM gold.fct_team_game_results) AS game_count,
        (SELECT count(*) FROM seasons) AS season_count,
        (SELECT min(season) FROM seasons) AS first_season,
        (SELECT max(season) FROM seasons) AS last_season
    """
)
