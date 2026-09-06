"""SQL against source.game_predictions (written by the ML job)."""

from __future__ import annotations

from sqlalchemy import text

INSERT_GAME_PREDICTION = text(
    """
    INSERT INTO source.game_predictions (
        game_id,
        as_of,
        model_name,
        model_version,
        home_team_id,
        away_team_id,
        model_wp,
        market_wp,
        scraped_at
    )
    VALUES (
        :game_id,
        :as_of,
        :model_name,
        :model_version,
        :home_team_id,
        :away_team_id,
        :model_wp,
        :market_wp,
        :scraped_at
    )
    ON CONFLICT (game_id, as_of, model_version) DO UPDATE SET
        model_name = EXCLUDED.model_name,
        home_team_id = EXCLUDED.home_team_id,
        away_team_id = EXCLUDED.away_team_id,
        model_wp = EXCLUDED.model_wp,
        market_wp = EXCLUDED.market_wp,
        scraped_at = EXCLUDED.scraped_at
    """
)
