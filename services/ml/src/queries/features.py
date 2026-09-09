"""SQL against the dbt-built, strictly as-of game feature relation."""

from __future__ import annotations

from sqlalchemy import text

SELECT_GAME_FEATURES = text(
    """
    SELECT
        game_id,
        season,
        season_type,
        game_date,
        home_team_id,
        away_team_id,
        home_won,
        home_games_before,
        away_games_before,
        point_diff_diff,
        win_pct_diff,
        last10_point_diff_diff,
        rest_days_diff,
        min_rest_days,
        travel_miles_diff,
        total_travel_miles,
        timezone_crossings_diff,
        total_timezone_crossings,
        h2h_games_before,
        h2h_home_win_pct
    FROM silver.int_game_features
    WHERE season_type = 'Regular Season'
    ORDER BY game_date, game_id
    """
)
