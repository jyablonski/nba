"""Scrape the current Basketball-Reference injury report into source.player_injuries.

This is a forward-looking snapshot (who is listed today), not a historical
ledger. Each run upserts the current set and deletes rows that left the report.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime

from db import get_session, upsert_rows
from models import PlayerInjury
from queries.snapshots import DELETE_STALE_PLAYER_INJURIES
from scrapers.contracts import bref_get
from scrapers.injuries_parse import INJURIES_URL, parse_injuries_html

logger = logging.getLogger(__name__)


def scrape_injuries(*, fetch_html: Callable[[str], str] | None = None) -> int:
    """Replace the current injury snapshot. Returns upserted row count."""
    fetch = fetch_html or bref_get
    html = fetch(INJURIES_URL)
    scraped_at = datetime.now()
    rows = parse_injuries_html(html, source_url=INJURIES_URL)
    for row in rows:
        row["scraped_at"] = scraped_at

    with get_session() as session:
        written = upsert_rows(
            session,
            PlayerInjury,
            rows,
            ["player_name_normalized", "bref_team_abbreviation"],
        )
        session.execute(DELETE_STALE_PLAYER_INJURIES, {"scraped_at": scraped_at})
        session.commit()
    logger.info("Upserted %s current injury rows from %s", written, INJURIES_URL)
    return written


__all__ = ["INJURIES_URL", "scrape_injuries"]
