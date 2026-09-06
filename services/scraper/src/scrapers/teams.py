"""Scrape static NBA team reference data into source.teams."""

from __future__ import annotations

import logging
from datetime import datetime

from nba_api.stats.static import teams as static_teams

from db import get_session, upsert_rows
from models import Team

logger = logging.getLogger(__name__)

# get_teams() has no conference/division; map from stable NBA team_ids.
TEAM_CONFERENCE_DIVISION: dict[int, tuple[str, str]] = {
    1610612738: ("East", "Atlantic"),  # BOS
    1610612751: ("East", "Atlantic"),  # BKN
    1610612752: ("East", "Atlantic"),  # NYK
    1610612755: ("East", "Atlantic"),  # PHI
    1610612761: ("East", "Atlantic"),  # TOR
    1610612741: ("East", "Central"),  # CHI
    1610612739: ("East", "Central"),  # CLE
    1610612765: ("East", "Central"),  # DET
    1610612754: ("East", "Central"),  # IND
    1610612749: ("East", "Central"),  # MIL
    1610612737: ("East", "Southeast"),  # ATL
    1610612766: ("East", "Southeast"),  # CHA
    1610612748: ("East", "Southeast"),  # MIA
    1610612753: ("East", "Southeast"),  # ORL
    1610612764: ("East", "Southeast"),  # WAS
    1610612743: ("West", "Northwest"),  # DEN
    1610612750: ("West", "Northwest"),  # MIN
    1610612760: ("West", "Northwest"),  # OKC
    1610612757: ("West", "Northwest"),  # POR
    1610612762: ("West", "Northwest"),  # UTA
    1610612744: ("West", "Pacific"),  # GSW
    1610612746: ("West", "Pacific"),  # LAC
    1610612747: ("West", "Pacific"),  # LAL
    1610612756: ("West", "Pacific"),  # PHX
    1610612758: ("West", "Pacific"),  # SAC
    1610612742: ("West", "Southwest"),  # DAL
    1610612745: ("West", "Southwest"),  # HOU
    1610612763: ("West", "Southwest"),  # MEM
    1610612740: ("West", "Southwest"),  # NOP
    1610612759: ("West", "Southwest"),  # SAS
}

# Historical NBA Stats MATCHUP codes and BRef spellings → current franchise abbreviation.
# source.teams stays the current 30; aliases resolve onto those team_ids (ids are stable).
TEAM_ABBREVIATION_ALIASES: dict[str, str] = {
    "NJN": "BKN",  # New Jersey Nets
    "BRK": "BKN",  # Basketball-Reference Brooklyn
    "NOH": "NOP",  # New Orleans Hornets
    "NOK": "NOP",  # New Orleans/Oklahoma City Hornets (Katrina)
    "SEA": "OKC",  # Seattle SuperSonics
    "CHO": "CHA",  # Basketball-Reference Charlotte
    "CHH": "CHA",  # original Charlotte Hornets (history with current CHA)
    "PHO": "PHX",  # Basketball-Reference Phoenix
}


def scrape_teams() -> int:
    scraped_at = datetime.now()
    rows: list[dict] = []
    for team in static_teams.get_teams():
        team_id = int(team["id"])
        conference, division = TEAM_CONFERENCE_DIVISION.get(team_id, ("", ""))
        if not conference or not division:
            logger.warning(
                "No conference/division mapping for team_id=%s (%s)",
                team_id,
                team.get("full_name"),
            )
            continue
        rows.append(
            {
                "team_id": team_id,
                "abbreviation": team["abbreviation"],
                "full_name": team["full_name"],
                "city": team["city"],
                "nickname": team["nickname"],
                "conference": conference,
                "division": division,
                "scraped_at": scraped_at,
            }
        )

    with get_session() as session:
        written = upsert_rows(session, Team, rows, ["team_id"])
    logger.info("Upserted %s teams", written)
    return written


def team_id_by_abbreviation(session) -> dict[str, int]:
    mapped = {row.abbreviation.upper(): row.team_id for row in session.query(Team).all()}
    if not mapped:
        mapped = {
            team["abbreviation"].upper(): int(team["id"]) for team in static_teams.get_teams()
        }
    return apply_team_abbreviation_aliases(mapped)


def apply_team_abbreviation_aliases(mapped: dict[str, int]) -> dict[str, int]:
    """Copy current-abbr → team_id and add historical/BRef keys for the same ids."""
    expanded = dict(mapped)
    for alias, current in TEAM_ABBREVIATION_ALIASES.items():
        team_id = mapped.get(current)
        if team_id is not None:
            expanded.setdefault(alias, team_id)
    return expanded


def resolve_team_id(abbr: str | None, mapped: dict[str, int]) -> int | None:
    """Look up team_id by current, historical, or BRef abbreviation."""
    if not abbr:
        return None
    key = abbr.strip().upper()
    if key in mapped:
        return mapped[key]
    current = TEAM_ABBREVIATION_ALIASES.get(key)
    if current:
        return mapped.get(current)
    return None
