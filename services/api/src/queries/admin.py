"""SQL for the operator admin view: ingestion, dbt, and ML health.

The only endpoints besides /api/v1/status that read the ``source`` schema.
Everything here is read-only and aggregate; the admin view reports, it does
not drive the pipeline.
"""

from sqlalchemy import text

# Gate row plus the same verdict decide_action() would reach, so the page can
# say "would not run right now" without reimplementing the rule in TypeScript.
ADMIN_PIPELINE_STATUS = text(
    """
    SELECT
        pipeline.enabled,
        pipeline.season_active,
        pipeline.season_start,
        pipeline.season_end,
        pipeline.scrape_mode,
        pipeline.target_season,
        pipeline.last_success_at,
        pipeline.last_scrape_date,
        pipeline.reason,
        pipeline.updated_at,
        CASE
            WHEN NOT pipeline.enabled THEN 'skipped_disabled'
            WHEN NOT pipeline.season_active THEN 'skipped_offseason'
            WHEN pipeline.season_start IS NOT NULL
                 AND CURRENT_DATE < pipeline.season_start THEN 'skipped_offseason'
            WHEN pipeline.season_end IS NOT NULL
                 AND CURRENT_DATE > pipeline.season_end THEN 'skipped_offseason'
            WHEN lower(coalesce(pipeline.scrape_mode, 'daily')) = 'none' THEN 'skipped_mode_none'
            WHEN lower(coalesce(pipeline.scrape_mode, 'daily')) = 'season'
                 AND pipeline.target_season IS NULL THEN 'noop'
            ELSE lower(coalesce(pipeline.scrape_mode, 'daily'))
        END AS action_today,
        pipeline.enabled AS reddit_would_run,
        EXTRACT(EPOCH FROM (now() - pipeline.last_success_at)) / 3600.0 AS hours_since_success
    FROM source.scrape_pipeline AS pipeline
    WHERE pipeline.id = 1
    """
)

ADMIN_RECENT_RUNS = text(
    """
    SELECT
        runs.run_id,
        runs.triggered_by,
        runs.status,
        runs.scrape_action,
        runs.scrape_exit,
        runs.reddit_ran,
        runs.reddit_exit,
        runs.dbt_exit,
        runs.detail,
        runs.started_at,
        runs.finished_at,
        EXTRACT(EPOCH FROM (runs.finished_at - runs.started_at)) AS duration_seconds
    FROM source.pipeline_runs AS runs
    ORDER BY runs.started_at DESC
    LIMIT :limit
    """
)

# Latest attempt per source, plus how many non-success runs have happened since
# that source last succeeded. One bad night is noise; a streak is a parse break.
ADMIN_SOURCE_HEALTH = text(
    """
    WITH latest AS (
        SELECT DISTINCT ON (source_runs.source_name)
            source_runs.source_name,
            source_runs.run_id,
            source_runs.status,
            source_runs.expectation,
            source_runs.rows_written,
            source_runs.attempt,
            source_runs.error_type,
            source_runs.error_detail,
            source_runs.started_at,
            source_runs.finished_at
        FROM source.scrape_source_runs AS source_runs
        ORDER BY source_runs.source_name, source_runs.started_at DESC, source_runs.id DESC
    ),
    last_success AS (
        SELECT
            successes.source_name,
            max(successes.started_at) AS succeeded_at
        FROM source.scrape_source_runs AS successes
        WHERE successes.status = 'success'
        GROUP BY successes.source_name
    ),
    since_success AS (
        SELECT
            attempts.source_name,
            count(*) AS runs_since_success
        FROM source.scrape_source_runs AS attempts
        LEFT JOIN last_success ON last_success.source_name = attempts.source_name
        -- Only 'failed' counts. A 'skipped' run is deliberate (off-day, no API
        -- key), so counting it would make every NBA source look like a growing
        -- failure streak through the off-season.
        WHERE attempts.status = 'failed'
          AND (
              last_success.succeeded_at IS NULL
              OR attempts.started_at > last_success.succeeded_at
          )
        GROUP BY attempts.source_name
    )
    SELECT
        latest.source_name,
        latest.run_id,
        latest.status,
        latest.expectation,
        latest.rows_written,
        latest.attempt,
        latest.error_type,
        latest.error_detail,
        latest.started_at,
        latest.finished_at,
        last_success.succeeded_at AS last_success_at,
        coalesce(since_success.runs_since_success, 0) AS runs_since_success
    FROM latest
    LEFT JOIN last_success ON last_success.source_name = latest.source_name
    LEFT JOIN since_success ON since_success.source_name = latest.source_name
    ORDER BY latest.source_name
    """
)

# Per-table watermarks. Deliberately explicit rather than looping over
# information_schema: the set of tables that matter is a product decision.
ADMIN_FRESHNESS = text(
    """
    SELECT 'games' AS table_name, max(scraped_at) AS scraped_at, count(*) AS row_count
    FROM source.games
    UNION ALL SELECT 'player_game_logs', max(scraped_at), count(*) FROM source.player_game_logs
    UNION ALL SELECT 'play_by_play', max(scraped_at), count(*) FROM source.play_by_play
    UNION ALL SELECT 'standings', max(scraped_at), count(*) FROM source.standings
    UNION ALL SELECT 'player_injuries', max(scraped_at), count(*) FROM source.player_injuries
    UNION ALL SELECT 'player_contracts', max(scraped_at), count(*) FROM source.player_contracts
    UNION ALL SELECT 'team_payroll', max(scraped_at), count(*) FROM source.team_payroll
    UNION ALL SELECT 'game_odds', max(scraped_at), count(*) FROM source.game_odds
    UNION ALL SELECT 'reddit_posts', max(scraped_at), count(*) FROM source.reddit_posts
    UNION ALL SELECT 'reddit_comments', max(scraped_at), count(*) FROM source.reddit_comments
    ORDER BY scraped_at DESC NULLS LAST
    """
)

# dbt health is inferred from the warehouse it produces. Gold table counts come
# from the catalog rather than count(*) per table on purpose: a fresh box has
# not run dbt yet, and a hardcoded `FROM gold.fct_x` fails to *parse* when the
# relation is missing, which would 500 the dashboard exactly when it is most
# needed. n_live_tup is approximate, which is fine at a glance.
ADMIN_DBT_STATUS = text(
    """
    SELECT
        (
            SELECT runs.dbt_exit
            FROM source.pipeline_runs AS runs
            WHERE runs.dbt_exit IS NOT NULL
            ORDER BY runs.started_at DESC
            LIMIT 1
        ) AS last_dbt_exit,
        (
            SELECT runs.started_at
            FROM source.pipeline_runs AS runs
            WHERE runs.dbt_exit IS NOT NULL
            ORDER BY runs.started_at DESC
            LIMIT 1
        ) AS last_dbt_run_at,
        (
            SELECT runs.run_id
            FROM source.pipeline_runs AS runs
            WHERE runs.dbt_exit IS NOT NULL
            ORDER BY runs.started_at DESC
            LIMIT 1
        ) AS last_dbt_run_id
    """
)

ADMIN_GOLD_TABLES = text(
    """
    SELECT
        gold_tables.relname AS table_name,
        greatest(gold_tables.n_live_tup, 0) AS row_count,
        gold_tables.last_analyze,
        gold_tables.last_autoanalyze
    FROM pg_stat_user_tables AS gold_tables
    WHERE gold_tables.schemaname = 'gold'
    ORDER BY gold_tables.relname
    """
)

ADMIN_ML_STATUS = text(
    """
    SELECT
        predictions.model_name,
        predictions.model_version,
        count(*) AS prediction_count,
        max(predictions.as_of) AS latest_as_of,
        max(predictions.scraped_at) AS latest_scraped_at,
        count(*) FILTER (WHERE predictions.market_wp IS NOT NULL) AS with_market_wp
    FROM source.game_predictions AS predictions
    GROUP BY predictions.model_name, predictions.model_version
    ORDER BY max(predictions.scraped_at) DESC
    """
)

# --- Operator job queue -------------------------------------------------
# The API enqueues only. A host-side runner claims and executes, because this
# process has no Docker socket and must never be given one.

INSERT_ADMIN_JOB = text(
    """
    INSERT INTO source.admin_jobs (job_type, requested_by, detail)
    VALUES (:job_type, :requested_by, :detail)
    RETURNING
        job_id,
        job_type,
        status,
        requested_by,
        exit_code,
        detail,
        log_tail,
        requested_at,
        started_at,
        finished_at
    """
)

SELECT_ADMIN_JOBS = text(
    """
    SELECT
        jobs.job_id,
        jobs.job_type,
        jobs.status,
        jobs.requested_by,
        jobs.exit_code,
        jobs.detail,
        jobs.log_tail,
        jobs.requested_at,
        jobs.started_at,
        jobs.finished_at
    FROM source.admin_jobs AS jobs
    ORDER BY jobs.requested_at DESC
    LIMIT :limit
    """
)
