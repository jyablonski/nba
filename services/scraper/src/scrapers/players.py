"""Scrape static player biographical data into source.players."""

from __future__ import annotations

import logging
from datetime import datetime

from nba_api.stats.static import players as static_players

from db import get_session, upsert_rows
from models import Player
from scrapers import NBA_REQUEST_TIMEOUT, dataset_rows, nba_call, parse_game_date, to_int, to_str

logger = logging.getLogger(__name__)


def scrape_players(*, enrich: bool = False) -> int:
    scraped_at = datetime.now()
    source = static_players.get_players()
    rows: list[dict] = []
    for raw in source:
        player_id = int(raw["id"])
        row = {
            "player_id": player_id,
            "first_name": raw.get("first_name") or "",
            "last_name": raw.get("last_name") or "",
            "full_name": raw.get("full_name")
            or f"{raw.get('first_name', '')} {raw.get('last_name', '')}".strip(),
            "is_active": bool(raw.get("is_active", False)),
            "jersey_number": None,
            "position": None,
            "height": None,
            "weight": None,
            "birth_date": None,
            "team_id": None,
            "from_year": None,
            "to_year": None,
            "scraped_at": scraped_at,
        }
        if enrich:
            extra = _best_effort_common_info(player_id)
            if extra:
                row.update(extra)
        rows.append(row)

    with get_session() as session:
        written = upsert_rows(session, Player, rows, ["player_id"])
    logger.info("Upserted %s players (enrich=%s)", written, enrich)
    return written


def upsert_player_stubs(players: list[dict]) -> int:
    """Insert minimal player rows so game-log FKs succeed for new players."""
    if not players:
        return 0
    scraped_at = datetime.now()
    rows = []
    for raw in players:
        full_name = raw.get("full_name") or ""
        first = raw.get("first_name") or (full_name.split(" ", 1)[0] if full_name else "")
        last = raw.get("last_name") or (full_name.split(" ", 1)[1] if " " in full_name else "")
        rows.append(
            {
                "player_id": int(raw["player_id"]),
                "first_name": first or "Unknown",
                "last_name": last or "Unknown",
                "full_name": full_name or f"{first} {last}".strip() or "Unknown",
                "is_active": bool(raw.get("is_active", True)),
                "jersey_number": None,
                "position": None,
                "height": None,
                "weight": None,
                "birth_date": None,
                "team_id": None,
                "from_year": None,
                "to_year": None,
                "scraped_at": scraped_at,
            }
        )
    with get_session() as session:
        return upsert_rows(session, Player, rows, ["player_id"])


def _best_effort_common_info(player_id: int) -> dict | None:
    try:
        from nba_api.stats.endpoints import commonplayerinfo

        endpoint = nba_call(
            lambda: commonplayerinfo.CommonPlayerInfo(
                player_id=player_id,
                timeout=NBA_REQUEST_TIMEOUT,
            )
        )
        payload = endpoint.get_normalized_dict()
        info_rows = dataset_rows(payload, "CommonPlayerInfo", "common_player_info")
        if not info_rows:
            return None
        info = info_rows[0]
        team_id = to_int(info.get("TEAM_ID"))
        if team_id == 0:
            team_id = None
        birth_raw = to_str(info.get("BIRTHDATE"))
        birth_date = None
        if birth_raw:
            try:
                birth_date = parse_game_date(birth_raw.split("T")[0])
            except ValueError:
                birth_date = None
        return {
            "jersey_number": to_str(info.get("JERSEY")),
            "position": to_str(info.get("POSITION")),
            "height": to_str(info.get("HEIGHT")),
            "weight": to_int(info.get("WEIGHT")),
            "birth_date": birth_date,
            "team_id": team_id,
            "from_year": to_int(info.get("FROM_YEAR")),
            "to_year": to_int(info.get("TO_YEAR")),
        }
    except Exception:
        logger.warning(
            "CommonPlayerInfo failed for player_id=%s; continuing",
            player_id,
            exc_info=False,
        )
        return None
