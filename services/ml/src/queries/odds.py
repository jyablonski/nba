"""SQL for optional market_wp attach (h2h de-vig average per game)."""

from __future__ import annotations

from sqlalchemy import text

SELECT_MARKET_WP_BY_GAME = text(
    """
    SELECT
        game_id,
        avg(home_market_wp) AS market_wp
    FROM silver.stg_game_odds
    WHERE market = 'h2h'
      AND game_id IS NOT NULL
      AND home_market_wp IS NOT NULL
    GROUP BY game_id
    """
)
