"""Scrape NBA Stats PlayByPlayV3 into source.play_by_play.

The CLI (``scrape-play-by-play``) loads Final games from ``source.games``
for one season (default ``current_season()``). Daily / pipeline passes
``game_ids`` for today's Finals only — not the whole season. Not on
``scrape-all``. Does not invent or scrape games.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any

from db import get_session, upsert_rows
from models import Game, PlayByPlay
from scrapers import (
    NBA_REQUEST_TIMEOUT,
    current_season,
    nba_call,
    row_get,
    to_int,
    to_str,
)
from scrapers.games import _is_final_status

logger = logging.getLogger(__name__)

# Flattened PlayByPlayV3 keys that become first-class columns.
_PROMOTED_KEYS = frozenset(
    {
        "gameid",
        "actionnumber",
        "actionid",
        "clock",
        "period",
        "teamid",
        "personid",
        "scorehome",
        "scoreaway",
        "actiontype",
        "subtype",
        "description",
    }
)

# V3 repeats actionNumber for paired events (turnover+steal, miss+block)
# with distinct actionId values. Grain is the triple.
_UPSERT_CONFLICT = ["game_id", "action_number", "action_id"]
_RICHNESS_KEYS = (
    "period",
    "clock",
    "score_home",
    "score_away",
    "team_id",
    "player_id",
    "action_type",
    "sub_type",
    "description",
)


class NoFinalGamesError(RuntimeError):
    """Raised when source.games has no Final rows for the requested season."""


def _optional_id(value: Any) -> int | None:
    parsed = to_int(value)
    if parsed is None or parsed == 0:
        return None
    return parsed


def _extras(raw: dict[str, Any]) -> dict[str, Any] | None:
    leftover: dict[str, Any] = {}
    for key, value in raw.items():
        if str(key).lower() in _PROMOTED_KEYS:
            continue
        if value is None or value == "":
            continue
        leftover[str(key)] = value
    return leftover or None


def map_play_by_play_action(
    raw: dict[str, Any],
    *,
    game_id: str,
    season: str,
    scraped_at: datetime,
) -> dict[str, Any] | None:
    """Map a PlayByPlayV3 action row. Skip if action_number is missing."""
    action_number = to_int(row_get(raw, "actionNumber", "ACTION_NUMBER", "EVENTNUM"))
    if action_number is None:
        return None
    row_game_id = to_str(row_get(raw, "gameId", "GAME_ID")) or game_id
    if not row_game_id:
        return None
    clock = to_str(row_get(raw, "clock", "CLOCK"))
    action_type = to_str(row_get(raw, "actionType", "ACTION_TYPE"))
    sub_type = to_str(row_get(raw, "subType", "SUB_TYPE"))
    description = to_str(row_get(raw, "description", "DESCRIPTION"))
    action_id = to_int(row_get(raw, "actionId", "ACTION_ID"))
    return {
        "game_id": row_game_id,
        "season": season,
        "action_number": action_number,
        "action_id": action_id if action_id is not None else action_number,
        "period": to_int(row_get(raw, "period", "PERIOD")),
        "clock": clock[:32] if clock else None,
        "score_home": to_int(row_get(raw, "scoreHome", "SCORE_HOME")),
        "score_away": to_int(row_get(raw, "scoreAway", "SCORE_AWAY")),
        "team_id": _optional_id(row_get(raw, "teamId", "TEAM_ID")),
        "player_id": _optional_id(row_get(raw, "personId", "PERSON_ID", "PLAYER_ID")),
        "action_type": action_type[:50] if action_type else None,
        "sub_type": sub_type[:80] if sub_type else None,
        "description": description,
        "extras": _extras(raw),
        "scraped_at": scraped_at,
    }


def _row_richness(row: dict[str, Any]) -> int:
    score = sum(1 for key in _RICHNESS_KEYS if row.get(key) not in (None, ""))
    extras = row.get("extras")
    if extras:
        score += len(extras)
    return score


def _dedupe_play_by_play_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per (game_id, action_number, action_id). Keep richest, else last."""
    chosen: dict[tuple[str, int, int | None], dict[str, Any]] = {}
    for row in rows:
        key = (row["game_id"], row["action_number"], row.get("action_id"))
        existing = chosen.get(key)
        if existing is None or _row_richness(row) >= _row_richness(existing):
            chosen[key] = row
    return list(chosen.values())


def _final_games_for_season(season: str) -> list[dict[str, str]]:
    with get_session() as session:
        rows = (
            session.query(Game.game_id, Game.season, Game.status)
            .filter(Game.season == season)
            .order_by(Game.game_id)
            .all()
        )
    return [
        {"game_id": game_id, "season": game_season}
        for game_id, game_season, status in rows
        if _is_final_status(status)
    ]


def _list_dataset(payload: dict[str, Any], *names: str) -> list[dict[str, Any]] | None:
    """Case-insensitive named list. None if the key is absent."""
    lookup = {str(key).lower(): value for key, value in payload.items()}
    for name in names:
        rows = lookup.get(name.lower())
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return None


def _actions_from_v3_payload(payload: Any) -> list[dict[str, Any]]:
    """Pull action rows from PlayByPlayV3 raw or normalized shapes.

    Raw ``get_dict()`` is ``{game: {actions: [...]}}``. nba_api 1.11.4
    ``get_normalized_dict()`` only understands legacy ``resultSets``, so it
    is empty for V3. Newer builds may expose ``PlayByPlay`` or ``Actions``.
    """
    if not isinstance(payload, dict):
        return []
    names = ("PlayByPlay", "Actions", "actions")
    found = _list_dataset(payload, *names)
    if found is not None:
        return found
    game = payload.get("game")
    if isinstance(game, dict):
        found = _list_dataset(game, *names)
        if found is not None:
            return found
    return []


def _payload_keys(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        return list(payload.keys())
    return [type(payload).__name__]


def _play_by_play_actions(game_id: str) -> list[dict[str, Any]]:
    from nba_api.stats.endpoints import playbyplayv3

    endpoint = nba_call(
        lambda: playbyplayv3.PlayByPlayV3(
            game_id=game_id,
            timeout=NBA_REQUEST_TIMEOUT,
        )
    )
    # Prefer the raw V3 body: 1.11.4 normalized dict is {} for this endpoint.
    raw = endpoint.get_dict()
    normalized = endpoint.get_normalized_dict()
    rows = _actions_from_v3_payload(raw) or _actions_from_v3_payload(normalized)
    if not rows:
        game = raw.get("game") if isinstance(raw, dict) else None
        nested = game if isinstance(game, dict) else {}
        actions = nested.get("actions")
        logger.warning(
            "PlayByPlayV3 empty game_id=%s normalized_keys=%s raw_keys=%s nested_keys=%s raw_rowcount=%s",
            game_id,
            _payload_keys(normalized),
            _payload_keys(raw),
            list(nested.keys()),
            len(actions) if isinstance(actions, list) else 0,
        )
    return rows


def scrape_play_by_play(
    season: str | None = None,
    *,
    game_ids: Sequence[str] | None = None,
    fetch_actions: Callable[[str], list[dict[str, Any]]] | None = None,
) -> int:
    """Upsert PlayByPlayV3 events for Final games.

    Without ``game_ids``, loads every Final in ``source.games`` for
    ``season`` (CLI backfill). With ``game_ids``, only those ids (daily
    path: today's Finals). An empty ``game_ids`` list is a no-op.
    """
    target = season or current_season()
    if game_ids is not None:
        games = [
            {"game_id": str(game_id).strip(), "season": target}
            for game_id in game_ids
            if str(game_id).strip()
        ]
        if not games:
            logger.info("Play-by-play skipped: no game_ids for %s", target)
            return 0
    else:
        games = _final_games_for_season(target)
        if not games:
            raise NoFinalGamesError(
                f"No Final games in source.games for {target}; run scrape-games first."
            )

    fetch = fetch_actions or _play_by_play_actions
    scraped_at = datetime.now()
    total = 0
    for index, game in enumerate(games, start=1):
        game_id = game["game_id"]
        try:
            raw_rows = fetch(game_id)
        except Exception:
            logger.warning("PlayByPlayV3 failed game_id=%s season=%s", game_id, target)
            continue
        mapped: list[dict[str, Any]] = []
        for raw in raw_rows:
            row = map_play_by_play_action(
                raw,
                game_id=game_id,
                season=target,
                scraped_at=scraped_at,
            )
            if row:
                mapped.append(row)
        mapped = _dedupe_play_by_play_rows(mapped)
        if not mapped:
            sample_keys = (
                list(raw_rows[0].keys()) if raw_rows and isinstance(raw_rows[0], dict) else []
            )
            logger.warning(
                "PlayByPlayV3 produced no rows game_id=%s season=%s raw_rowcount=%s sample_keys=%s",
                game_id,
                target,
                len(raw_rows),
                sample_keys,
            )
        if mapped:
            with get_session() as session:
                total += upsert_rows(
                    session,
                    PlayByPlay,
                    mapped,
                    _UPSERT_CONFLICT,
                )
        if index % 25 == 0 or index == len(games):
            logger.info(
                "Play-by-play %s/%s Final games for %s (%s events so far)",
                index,
                len(games),
                target,
                total,
            )
    return total


__all__ = [
    "NoFinalGamesError",
    "map_play_by_play_action",
    "scrape_play_by_play",
]
