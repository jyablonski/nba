"""SQL against gold player dims, game logs, and season stats."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import bindparam, text

COMPARE_STAT_COLUMNS = {
    "games_played": "career_games_played",
    "career_games_played": "career_games_played",
    "ppg": "career_ppg",
    "career_ppg": "career_ppg",
    "rpg": "career_rpg",
    "career_rpg": "career_rpg",
    "apg": "career_apg",
    "career_apg": "career_apg",
    "plus_minus": "career_avg_plus_minus",
    "career_plus_minus": "career_avg_plus_minus",
    "career_avg_plus_minus": "career_avg_plus_minus",
}

COMPARE_ORDER_EXPR = {
    "career_games_played": "p.career_games_played",
    "career_ppg": "p.career_ppg",
    "career_rpg": "p.career_rpg",
    "career_apg": "p.career_apg",
    "career_avg_plus_minus": "career_pm.career_avg_plus_minus",
}

GAME_LOG_SORT_COLUMNS = {
    "game_date": "game_date",
    "date": "game_date",
    "opponent": "opponent_abbreviation",
    "opponent_abbreviation": "opponent_abbreviation",
    "location": "location",
    "result": "result",
    "minutes": "minutes",
    "points": "points",
    "rebounds": "rebounds",
    "assists": "assists",
    "steals": "steals",
    "blocks": "blocks",
    "turnovers": "turnovers",
    "plus_minus": "plus_minus",
    "is_back_to_back": "is_back_to_back",
}

PLAYER_EXISTS = text("SELECT 1 FROM gold.dim_players WHERE player_id = :player_id")

LIST_PLAYERS_COUNT = text(
    """
    SELECT count(*) AS total
    FROM gold.dim_players p
    LEFT JOIN gold.dim_teams t ON t.team_id = p.team_id
    WHERE (:search IS NULL OR p.full_name ILIKE :search)
      AND (:active IS NULL OR p.is_active = :active)
      AND (:team_id IS NULL OR p.team_id = :team_id)
    """
)

LIST_PLAYERS = text(
    """
    SELECT
        p.player_id,
        p.full_name,
        p.position,
        t.abbreviation AS team_abbreviation,
        p.is_active,
        coalesce(p.career_games_played, 0) AS career_games_played,
        p.career_ppg,
        p.career_rpg,
        p.career_apg
    FROM gold.dim_players p
    LEFT JOIN gold.dim_teams t ON t.team_id = p.team_id
    WHERE (:search IS NULL OR p.full_name ILIKE :search)
      AND (:active IS NULL OR p.is_active = :active)
      AND (:team_id IS NULL OR p.team_id = :team_id)
    ORDER BY p.full_name
    LIMIT :limit OFFSET :offset
    """
)

PLAYER_BY_ID = text(
    """
    SELECT
        p.player_id,
        p.full_name,
        p.position,
        t.abbreviation AS team_abbreviation,
        p.is_active,
        p.first_name,
        p.last_name,
        p.height,
        p.weight,
        p.birth_date,
        coalesce(p.career_games_played, 0) AS career_games_played,
        coalesce(p.seasons_played, 0) AS seasons_played,
        p.first_season,
        p.last_season,
        p.career_ppg,
        p.career_rpg,
        p.career_apg,
        p.current_season_salary,
        p.current_remaining_guaranteed,
        p.current_contract_season
    FROM gold.dim_players p
    LEFT JOIN gold.dim_teams t ON t.team_id = p.team_id
    WHERE p.player_id = :player_id
    """
)

PLAYER_NAME = text(
    """
    SELECT player_id, full_name
    FROM gold.dim_players
    WHERE player_id = :player_id
    """
)

GAME_LOG_FILTERS = """
    player_id = :player_id
      AND (:season IS NULL OR season = :season)
      AND (:is_back_to_back IS NULL OR is_back_to_back = :is_back_to_back)
"""

LIST_GAME_LOGS_COUNT = text(
    f"""
    SELECT count(*) AS total
    FROM gold.fct_player_game_logs
    WHERE {GAME_LOG_FILTERS}
    """
)

LIST_SEASON_STATS_COUNT = text(
    """
    SELECT count(*) AS total
    FROM gold.fct_player_season_stats
    WHERE player_id = :player_id
    """
)

LIST_SEASON_STATS = text(
    """
    SELECT
        player_id,
        season,
        games_played,
        ppg,
        rpg,
        apg
    FROM gold.fct_player_season_stats
    WHERE player_id = :player_id
    ORDER BY season
    LIMIT :limit OFFSET :offset
    """
)

BACK_TO_BACK_STATS = text(
    """
    SELECT
        count(*) FILTER (WHERE is_back_to_back) AS total_back_to_backs,
        count(*) FILTER (
            WHERE is_back_to_back AND coalesce(minutes, 0) > 0
        ) AS games_played_in_b2b,
        count(*) FILTER (
            WHERE is_back_to_back AND coalesce(minutes, 0) = 0
        ) AS games_sat_in_b2b,
        round(
            avg(points) FILTER (WHERE is_back_to_back)::numeric, 1
        ) AS avg_pts_b2b,
        round(
            avg(points) FILTER (
                WHERE NOT coalesce(is_back_to_back, false)
            )::numeric,
            1
        ) AS avg_pts_non_b2b
    FROM gold.fct_player_game_logs
    WHERE player_id = :player_id
      AND (:season IS NULL OR season = :season)
    """
)


def list_game_logs_stmt(order_column: str, descending: bool):
    direction = "DESC" if descending else "ASC"
    return text(
        f"""
        SELECT
            game_date,
            coalesce(opponent_abbreviation, '') AS opponent_abbreviation,
            coalesce(location, '') AS location,
            coalesce(result, '') AS result,
            minutes,
            points,
            rebounds,
            assists,
            steals,
            blocks,
            turnovers,
            plus_minus,
            coalesce(is_back_to_back, false) AS is_back_to_back
        FROM gold.fct_player_game_logs
        WHERE {GAME_LOG_FILTERS}
        ORDER BY {order_column} {direction} NULLS LAST, career_game_number DESC
        LIMIT :limit OFFSET :offset
        """
    )


PLAYERS_BY_IDS = text(
    """
    SELECT
        p.player_id,
        p.full_name
    FROM gold.dim_players p
    WHERE p.player_id IN :player_ids
    """
).bindparams(bindparam("player_ids", expanding=True))

# Opposite-team meetings only (same game_id, not teammates). Warehouse logs start 2010-11.
HEAD_TO_HEAD_LOGS = text(
    """
    WITH left_logs AS (
        SELECT player_id, game_id, team_id
        FROM gold.fct_player_game_logs
        WHERE player_id = :player_a
    ),
    right_logs AS (
        SELECT player_id, game_id, team_id
        FROM gold.fct_player_game_logs
        WHERE player_id = :player_b
    ),
    opposed AS (
        SELECT left_logs.game_id
        FROM left_logs
        INNER JOIN right_logs ON left_logs.game_id = right_logs.game_id
        WHERE left_logs.team_id IS DISTINCT FROM right_logs.team_id
    )
    SELECT
        logs.player_id,
        coalesce(logs.player_name, '') AS full_name,
        logs.game_id,
        logs.game_date,
        logs.season,
        coalesce(logs.matchup, '') AS matchup,
        coalesce(logs.team_abbreviation, '') AS team_abbreviation,
        coalesce(logs.opponent_abbreviation, '') AS opponent_abbreviation,
        coalesce(logs.location, '') AS location,
        coalesce(logs.result, '') AS result,
        logs.minutes,
        logs.points,
        logs.rebounds,
        logs.assists,
        logs.steals,
        logs.blocks,
        logs.turnovers,
        logs.plus_minus
    FROM gold.fct_player_game_logs AS logs
    INNER JOIN opposed ON logs.game_id = opposed.game_id
    WHERE logs.player_id IN (:player_a, :player_b)
    ORDER BY logs.game_date DESC, logs.game_id, logs.player_id
    """
)


def _mean(values: list[float | int | None]) -> float | None:
    present = [float(value) for value in values if value is not None]
    if not present:
        return None
    return round(sum(present) / len(present), 1)


def build_head_to_head(
    players: list[dict],
    logs: list[dict],
    player_ids: list[UUID],
) -> dict:
    names = {row["player_id"]: row["full_name"] for row in players}
    by_player: dict[UUID, list[dict]] = {player_id: [] for player_id in player_ids}
    games: list[dict] = []
    grouped: dict[str, dict] = {}

    for row in logs:
        player_id = row["player_id"]
        if player_id in by_player:
            by_player[player_id].append(row)
        game_id = row["game_id"]
        game = grouped.get(game_id)
        if game is None:
            game = {
                "game_id": game_id,
                "game_date": row["game_date"],
                "season": row["season"],
                "matchup": row["matchup"],
                "lines": [],
            }
            grouped[game_id] = game
            games.append(game)
        game["lines"].append(
            {
                "player_id": player_id,
                "full_name": names.get(player_id) or row["full_name"],
                "team_abbreviation": row["team_abbreviation"],
                "opponent_abbreviation": row["opponent_abbreviation"],
                "location": row["location"],
                "result": row["result"],
                "minutes": row["minutes"],
                "points": row["points"],
                "rebounds": row["rebounds"],
                "assists": row["assists"],
                "steals": row.get("steals"),
                "blocks": row.get("blocks"),
                "turnovers": row.get("turnovers"),
                "plus_minus": row.get("plus_minus"),
            }
        )

    for game in games:
        game["lines"].sort(key=lambda line: player_ids.index(line["player_id"]))

    averages = []
    for player_id in player_ids:
        rows = by_player[player_id]
        averages.append(
            {
                "player_id": player_id,
                "full_name": names[player_id],
                "games": len(rows),
                "mpg": _mean([row["minutes"] for row in rows]),
                "ppg": _mean([row["points"] for row in rows]),
                "rpg": _mean([row["rebounds"] for row in rows]),
                "apg": _mean([row["assists"] for row in rows]),
                "plus_minus": _mean([row.get("plus_minus") for row in rows]),
            }
        )

    return {
        "games_played": len(games),
        "players": averages,
        "games": games,
    }


def compare_players_stmt(order_column: str):
    order_expr = COMPARE_ORDER_EXPR.get(order_column)
    if order_expr is None:
        raise ValueError(f"Unsupported compare order column '{order_column}'")
    return text(
        f"""
        SELECT
            p.player_id,
            p.full_name,
            t.abbreviation AS team_abbreviation,
            p.position,
            coalesce(p.career_games_played, 0) AS career_games_played,
            coalesce(p.seasons_played, 0) AS seasons_played,
            p.first_season,
            p.last_season,
            p.career_ppg,
            p.career_rpg,
            p.career_apg,
            career_pm.career_avg_plus_minus
        FROM gold.dim_players p
        LEFT JOIN gold.dim_teams t ON t.team_id = p.team_id
        LEFT JOIN (
            SELECT
                player_id,
                round(avg(plus_minus)::numeric, 1) AS career_avg_plus_minus
            FROM gold.fct_player_game_logs
            GROUP BY player_id
        ) career_pm ON career_pm.player_id = p.player_id
        WHERE p.player_id IN :player_ids
        ORDER BY {order_expr} DESC NULLS LAST, p.full_name
        """
    ).bindparams(bindparam("player_ids", expanding=True))
