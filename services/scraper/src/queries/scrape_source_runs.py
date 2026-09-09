"""SQL against ``source.scrape_source_runs`` (per-source run history)."""

from __future__ import annotations

from sqlalchemy import text

INSERT_SOURCE_RUN = text(
    """
    INSERT INTO source.scrape_source_runs (
        run_id,
        source_name,
        status,
        expectation,
        rows_written,
        season,
        attempt,
        error_type,
        error_detail,
        started_at,
        finished_at
    )
    VALUES (
        :run_id,
        :source_name,
        :status,
        :expectation,
        :rows_written,
        :season,
        :attempt,
        :error_type,
        :error_detail,
        :started_at,
        :finished_at
    )
    """
)

# Latest attempt per source for one run; drives retry selection and the digest.
SELECT_SOURCE_RUNS_FOR_RUN = text(
    """
    SELECT DISTINCT ON (source_name)
        source_name,
        status,
        expectation,
        rows_written,
        attempt,
        error_type,
        error_detail
    FROM source.scrape_source_runs
    WHERE run_id = :run_id
    ORDER BY source_name, attempt DESC, id DESC
    """
)
