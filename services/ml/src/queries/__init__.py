"""SQL for gold reads and source prediction writes."""

from queries.games import SELECT_REGULAR_SEASON_FINALS, SELECT_UPCOMING_GAMES
from queries.odds import SELECT_MARKET_WP_BY_GAME
from queries.predictions import INSERT_GAME_PREDICTION

__all__ = [
    "INSERT_GAME_PREDICTION",
    "SELECT_MARKET_WP_BY_GAME",
    "SELECT_REGULAR_SEASON_FINALS",
    "SELECT_UPCOMING_GAMES",
]
