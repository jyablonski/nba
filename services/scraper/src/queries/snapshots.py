"""SQL for current-snapshot replace (injuries / odds)."""

from __future__ import annotations

from sqlalchemy import text

DELETE_STALE_PLAYER_INJURIES = text(
    """
    DELETE FROM source.player_injuries
    WHERE scraped_at < :scraped_at
    """
)

DELETE_STALE_GAME_ODDS = text(
    """
    DELETE FROM source.game_odds
    WHERE scraped_at < :scraped_at
    """
)
