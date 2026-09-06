"""SQL against ``source.scrape_pipeline`` (singleton pipeline gate)."""

from __future__ import annotations

from sqlalchemy import text

SELECT_PIPELINE_CONFIG = text(
    """
    SELECT
        enabled,
        season_active,
        season_start,
        season_end,
        scrape_mode,
        target_season,
        last_success_at,
        last_scrape_date,
        reason,
        updated_at
    FROM source.scrape_pipeline
    WHERE id = 1
    """
)

UPDATE_PIPELINE_ENABLED = text(
    """
    UPDATE source.scrape_pipeline
    SET
        enabled = :enabled,
        season_active = COALESCE(:season_active, season_active),
        season_start = COALESCE(:season_start, season_start),
        season_end = COALESCE(:season_end, season_end),
        scrape_mode = COALESCE(:scrape_mode, scrape_mode),
        target_season = COALESCE(:target_season, target_season),
        reason = COALESCE(:reason, reason),
        updated_at = NOW()
    WHERE id = 1
    """
)

UPDATE_PIPELINE_SUCCESS = text(
    """
    UPDATE source.scrape_pipeline
    SET
        last_success_at = NOW(),
        last_scrape_date = COALESCE(:scrape_date, CURRENT_DATE),
        updated_at = NOW()
    WHERE id = 1
    """
)
