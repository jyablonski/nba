"""Named tools over Cube (same operations as MCP). No gold SQL."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from cube.analytics import CubeAnalytics
from cube.errors import CubeError, UnknownMemberError

NAMED_TOOL_NAMES = frozenset(
    {
        "search_players",
        "get_player_game_log",
        "get_player_back_to_backs",
        "get_career_stats",
        "compare_players",
        "get_team_record",
        "get_player_contract",
        "get_team_payroll",
        "get_standings",
        "get_player_season_stats",
        "get_games_schedule",
        "get_game_predictions",
        "get_player_injuries",
        "get_game_odds",
        "get_play_by_play",
        "get_reddit_posts",
        "query_cube",
        "run_cube_query",
    }
)


def _function_schema(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
            },
        },
    }


def named_tool_schemas() -> list[dict[str, Any]]:
    return [
        _function_schema(
            "search_players",
            "Fuzzy search for NBA players by name (Cube players).",
            {"name": {"type": "string"}},
            ["name"],
        ),
        _function_schema(
            "get_player_game_log",
            "Game-by-game box scores for a player via Cube player_game_logs.",
            {
                "player_id": {"type": "string"},
                "season": {"type": "string"},
            },
            ["player_id"],
        ),
        _function_schema(
            "get_player_back_to_backs",
            "Back-to-back volume and scoring splits for a player via Cube.",
            {
                "player_id": {"type": "string"},
                "season": {"type": "string"},
            },
            ["player_id"],
        ),
        _function_schema(
            "get_career_stats",
            "Career totals and averages for a player via Cube players.",
            {"player_id": {"type": "string"}},
            ["player_id"],
        ),
        _function_schema(
            "compare_players",
            "Side-by-side career rows for two or more players via Cube.",
            {
                "player_ids": {"type": "array", "items": {"type": "string"}},
                "stats": {"type": "array", "items": {"type": "string"}},
            },
            ["player_ids"],
        ),
        _function_schema(
            "get_team_record",
            "Team W/L with optional opponent, location, arena-city, and season filters via Cube team_games.",
            {
                "team_abbreviation": {"type": "string"},
                "opponent_abbreviation": {"type": "string"},
                "location": {"type": "string"},
                "arena_city": {"type": "string"},
                "since_season": {"type": "string"},
                "season": {"type": "string"},
            },
            ["team_abbreviation"],
        ),
        _function_schema(
            "get_player_contract",
            "Remaining-season salary snapshot via Cube players, or player_contracts when season is set.",
            {
                "player_id": {"type": "string"},
                "season": {"type": "string"},
            },
            ["player_id"],
        ),
        _function_schema(
            "get_team_payroll",
            "Team payroll snapshot via Cube teams, or team_payroll when season is set.",
            {
                "team_abbreviation": {"type": "string"},
                "season": {"type": "string"},
            },
            ["team_abbreviation"],
        ),
        _function_schema(
            "get_standings",
            "Conference standings via Cube standings, or Regular Season team_games W–L ranks when official rows are missing.",
            {
                "season": {"type": "string"},
                "conference": {"type": "string"},
            },
        ),
        _function_schema(
            "get_player_season_stats",
            "Per-season PPG / RPG / APG for a player via Cube player_season_stats.",
            {"player_id": {"type": "string"}},
            ["player_id"],
        ),
        _function_schema(
            "get_games_schedule",
            "All-status slate via Cube games_schedule (upcoming scores are null).",
            {
                "season": {"type": "string"},
                "status": {"type": "string"},
            },
        ),
        _function_schema(
            "get_game_predictions",
            "Champion pregame home win probability (model_wp; away_wp is 1 - model_wp, as_of, model_version). Not a betting line.",
            {
                "game_id": {"type": "string"},
                "upcoming": {"type": "boolean"},
            },
        ),
        _function_schema(
            "get_player_injuries",
            "Current Basketball-Reference injury snapshot via Cube player_injuries.",
            {
                "player_id": {"type": "string"},
                "team_abbreviation": {"type": "string"},
            },
        ),
        _function_schema(
            "get_game_odds",
            "Current Odds API upcoming-slate snapshot. Market snapshot, not a book.",
            {"game_id": {"type": "string"}},
        ),
        _function_schema(
            "get_play_by_play",
            "Play-by-play actions for one game via Cube play_by_play. Season-scoped ingest; sane limit.",
            {
                "game_id": {"type": "string"},
                "limit": {"type": "integer"},
            },
            ["game_id"],
        ),
        _function_schema(
            "get_reddit_posts",
            "Reddit submissions via Cube reddit_posts. Optional title search.",
            {
                "search": {"type": "string"},
                "limit": {"type": "integer"},
            },
        ),
        _function_schema(
            "query_cube",
            "Load a Cube query. Members must exist in Cube meta. No SQL.",
            {
                "measures": {"type": "array", "items": {"type": "string"}},
                "dimensions": {"type": "array", "items": {"type": "string"}},
                "filters": {"type": "array", "items": {"type": "object"}},
                "timeDimensions": {"type": "array", "items": {"type": "object"}},
                "limit": {"type": "integer"},
            },
        ),
    ]


class NamedToolExecutor:
    """Run named tools against Cube. Never executes model SQL."""

    def __init__(self, cube: CubeAnalytics) -> None:
        self.cube = cube
        self.executed: list[str] = []

    def schemas(self) -> list[dict[str, Any]]:
        return named_tool_schemas()

    def execute(self, name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
        args = arguments or {}
        self.executed.append(name)
        handler = {
            "search_players": self._search_players,
            "get_player_game_log": self._game_log,
            "get_player_back_to_backs": self._back_to_backs,
            "get_career_stats": self._career_stats,
            "compare_players": self._compare,
            "get_team_record": self._team_record,
            "get_player_contract": self._player_contract,
            "get_team_payroll": self._team_payroll,
            "get_standings": self._standings,
            "get_player_season_stats": self._season_stats,
            "get_games_schedule": self._games_schedule,
            "get_game_predictions": self._game_predictions,
            "get_player_injuries": self._player_injuries,
            "get_game_odds": self._game_odds,
            "get_play_by_play": self._play_by_play,
            "get_reddit_posts": self._reddit_posts,
            "query_cube": self._query_cube,
            "run_cube_query": self._query_cube,
        }.get(name)
        if handler is None:
            return {"ok": False, "error": f"Unknown tool '{name}'"}
        try:
            return handler(args)
        except UnknownMemberError as exc:
            return {"ok": False, "error": str(exc)}
        except CubeError as exc:
            return {"ok": False, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001 — tool errors become model-visible JSON
            return {"ok": False, "error": str(exc)}

    def _search_players(self, args: dict[str, Any]) -> dict[str, Any]:
        name = str(args.get("name") or "").strip()
        return {"ok": True, "rows": self.cube.search_players(name)}

    def _game_log(self, args: dict[str, Any]) -> dict[str, Any]:
        rows = self.cube.get_player_game_log(UUID(str(args["player_id"])), args.get("season"))
        return {"ok": True, "rows": rows}

    def _back_to_backs(self, args: dict[str, Any]) -> dict[str, Any]:
        stats = self.cube.get_back_to_back_stats(UUID(str(args["player_id"])), args.get("season"))
        return {"ok": True, "row": stats}

    def _career_stats(self, args: dict[str, Any]) -> dict[str, Any]:
        player = self.cube.get_career_stats(UUID(str(args["player_id"])))
        if player is None:
            return {"ok": False, "error": "Player not found."}
        return {"ok": True, "row": player}

    def _compare(self, args: dict[str, Any]) -> dict[str, Any]:
        ids = [UUID(str(pid)) for pid in (args.get("player_ids") or [])]
        stats = args.get("stats")
        rows = self.cube.compare_players(ids, stats)
        return {"ok": True, "rows": rows}

    def _team_record(self, args: dict[str, Any]) -> dict[str, Any]:
        abbr = str(args.get("team_abbreviation") or "").upper()
        team = self.cube.find_team(abbr)
        if team is None:
            return {"ok": False, "error": f"No team found for abbreviation '{abbr}'."}
        record = self.cube.get_team_record(
            abbr,
            opponent_abbreviation=args.get("opponent_abbreviation"),
            location=args.get("location"),
            season=args.get("season"),
            since_season=args.get("since_season"),
            arena_city=args.get("arena_city"),
        )
        return {"ok": True, "row": record}

    def _player_contract(self, args: dict[str, Any]) -> dict[str, Any]:
        player = self.cube.get_player_contract(UUID(str(args["player_id"])), args.get("season"))
        if player is None:
            return {"ok": False, "error": "Player not found."}
        return {"ok": True, "row": player}

    def _team_payroll(self, args: dict[str, Any]) -> dict[str, Any]:
        abbr = str(args.get("team_abbreviation") or "").upper()
        team = self.cube.get_team_payroll(abbr, args.get("season"))
        if team is None:
            return {"ok": False, "error": f"No team found for abbreviation '{abbr}'."}
        return {"ok": True, "row": team}

    def _standings(self, args: dict[str, Any]) -> dict[str, Any]:
        rows = self.cube.list_standings(
            season=args.get("season"),
            conference=args.get("conference"),
        )
        return {"ok": True, "rows": rows}

    def _season_stats(self, args: dict[str, Any]) -> dict[str, Any]:
        rows = self.cube.get_player_season_stats(UUID(str(args["player_id"])))
        return {"ok": True, "rows": rows}

    def _games_schedule(self, args: dict[str, Any]) -> dict[str, Any]:
        rows = self.cube.get_games_schedule(
            season=args.get("season"),
            status=args.get("status"),
        )
        return {"ok": True, "rows": rows}

    def _game_predictions(self, args: dict[str, Any]) -> dict[str, Any]:
        rows = self.cube.get_game_predictions(
            game_id=UUID(str(args["game_id"])) if args.get("game_id") else None,
            upcoming=bool(args.get("upcoming")),
        )
        return {"ok": True, "rows": rows}

    def _player_injuries(self, args: dict[str, Any]) -> dict[str, Any]:
        player_id = args.get("player_id")
        rows = self.cube.get_player_injuries(
            player_id=UUID(str(player_id)) if player_id is not None else None,
            team_abbreviation=args.get("team_abbreviation"),
        )
        return {"ok": True, "rows": rows}

    def _game_odds(self, args: dict[str, Any]) -> dict[str, Any]:
        rows = self.cube.get_game_odds(
            game_id=UUID(str(args["game_id"])) if args.get("game_id") else None
        )
        return {"ok": True, "rows": rows}

    def _play_by_play(self, args: dict[str, Any]) -> dict[str, Any]:
        rows = self.cube.get_play_by_play(UUID(str(args["game_id"])), args.get("limit"))
        return {"ok": True, "rows": rows}

    def _reddit_posts(self, args: dict[str, Any]) -> dict[str, Any]:
        rows = self.cube.get_reddit_posts(search=args.get("search"), limit=args.get("limit"))
        return {"ok": True, "rows": rows}

    def _query_cube(self, args: dict[str, Any]) -> dict[str, Any]:
        query = {
            key: args[key]
            for key in ("measures", "dimensions", "filters", "timeDimensions", "limit")
            if key in args and args[key] is not None
        }
        rows = self.cube.run_cube_query(query)
        return {"ok": True, "rows": rows}
