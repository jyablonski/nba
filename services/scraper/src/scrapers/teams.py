"""Load the repo-owned franchise catalog into the source schema."""

from __future__ import annotations

import logging

from identity import seed_team_catalog

from db import get_session

logger = logging.getLogger(__name__)


def scrape_teams() -> int:
    """Seed teams and their BRef crosswalk without an HTTP request."""
    with get_session() as session:
        written = seed_team_catalog(session)
    logger.info("Loaded %s canonical teams from the Baseline catalog", written)
    return written


__all__ = ["scrape_teams"]
