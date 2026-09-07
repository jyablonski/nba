"""Discover and maintain the durable player registry from BRef rosters."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from bs4 import BeautifulSoup, Comment, Tag
from identity import BREF_PROVIDER, ensure_player, seed_team_catalog

from db import get_session
from models import Player
from scrapers import BREF_BASE_URL, bref_get, current_season, season_start_year, to_int
from scrapers.contracts_parse import PLAYER_HREF_RE, normalize_player_name

logger = logging.getLogger(__name__)

ROSTER_TABLE_ID = "roster"


def team_roster_url(bref_abbreviation: str, season: str | None = None) -> str:
    year = season_start_year(season or current_season())
    return f"{BREF_BASE_URL}/teams/{bref_abbreviation.upper()}/{year}.html"


def _find_roster_table(soup: BeautifulSoup) -> Tag | None:
    table = soup.find("table", id=ROSTER_TABLE_ID)
    if isinstance(table, Tag):
        return table
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        if 'id="roster"' not in comment and "id='roster'" not in comment:
            continue
        nested = BeautifulSoup(str(comment), "html.parser")
        table = nested.find("table", id=ROSTER_TABLE_ID)
        if isinstance(table, Tag):
            return table
    return None


def _cell_text(row: Tag, stat: str) -> str | None:
    cell = row.find(["th", "td"], attrs={"data-stat": stat})
    if not isinstance(cell, Tag):
        return None
    value = cell.get("csk") or cell.get_text(" ", strip=True)
    return str(value).strip() or None


def _player_cell(row: Tag) -> tuple[str | None, str | None]:
    cell = row.find(["th", "td"], attrs={"data-stat": "player"})
    if not isinstance(cell, Tag):
        return None, None
    link = cell.find("a")
    if not isinstance(link, Tag):
        return None, cell.get_text(" ", strip=True) or None
    href = str(link.get("href") or "")
    match = PLAYER_HREF_RE.search(href)
    return (match.group(1).lower() if match else None), link.get_text(" ", strip=True) or None


def _parse_years(value: str | None) -> tuple[int | None, int | None]:
    years = [int(item) for item in re.findall(r"\b(\d{4})\b", value or "")]
    if not years:
        return None, None
    return min(years), max(years)


def parse_roster_html(html: str, *, team_id: Any, source_url: str) -> list[dict[str, Any]]:
    """Parse BRef's roster table into provider-keyed player records."""
    soup = BeautifulSoup(html, "html.parser")
    table = _find_roster_table(soup)
    if table is None:
        return []
    rows: list[dict[str, Any]] = []
    for row in table.select("tbody tr"):
        if not isinstance(row, Tag) or "thead" in (row.get("class") or []):
            continue
        slug, name = _player_cell(row)
        if not slug or not name or name.lower() == "player":
            continue
        first, _, last = name.partition(" ")
        from_year, to_year = _parse_years(_cell_text(row, "years"))
        rows.append(
            {
                "provider": BREF_PROVIDER,
                "external_id": slug,
                "source_url": source_url,
                "first_name": first,
                "last_name": last or first,
                "full_name": name,
                "player_name_normalized": normalize_player_name(name),
                "is_active": True,
                "jersey_number": _cell_text(row, "number"),
                "position": _cell_text(row, "pos"),
                "height": _cell_text(row, "height"),
                "weight": to_int(_cell_text(row, "weight")),
                "birth_date": _parse_birth_date(_cell_text(row, "birth_date")),
                "from_year": from_year,
                "to_year": to_year,
                "team_id": team_id,
            }
        )
    return rows


def _parse_birth_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def scrape_players(
    *,
    season: str | None = None,
    fetch_html: Callable[[str], str] | None = None,
) -> int:
    """Load current rosters from Basketball-Reference team pages."""
    target_season = season or current_season()
    fetch = fetch_html or bref_get
    scraped_at = datetime.now()
    # Keep the HTTP phase outside the transaction while preserving deterministic order.
    from catalog.teams import TEAM_CATALOG

    all_rows: list[dict[str, Any]] = []
    for entry in TEAM_CATALOG:
        url = team_roster_url(entry.bref_abbreviation, target_season)
        try:
            all_rows.extend(parse_roster_html(fetch(url), team_id=entry.team_id, source_url=url))
        except Exception:
            logger.exception("BRef roster scrape failed for %s", url)
    written = 0
    with get_session() as session:
        seed_team_catalog(session, scraped_at=scraped_at)
        for row in all_rows:
            player_id = ensure_player(
                session,
                provider=row.pop("provider"),
                external_id=row.pop("external_id"),
                full_name=row.pop("full_name"),
                source_url=row.pop("source_url"),
                team_id=row.pop("team_id"),
                is_active=row.pop("is_active"),
                metadata={
                    key: value
                    for key, value in row.items()
                    if key not in {"first_name", "last_name"}
                },
            )
            player = session.get(Player, player_id)
            if player is None:
                continue
            for key, value in row.items():
                if hasattr(player, key) and value is not None:
                    setattr(player, key, value)
            player.scraped_at = scraped_at
            written += 1
    logger.info("Upserted %s BRef roster players for %s", written, target_season)
    return written


__all__ = ["parse_roster_html", "scrape_players", "team_roster_url"]
