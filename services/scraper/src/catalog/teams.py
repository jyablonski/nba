"""The Baseline franchise catalog.

This module is deliberately provider-free. The UUIDs are explicit values owned by
Baseline; BRef abbreviations and historical spellings are catalog data, not
identity keys derived from a provider response.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class TeamCatalogEntry:
    team_id: UUID
    canonical_slug: str
    abbreviation: str
    full_name: str
    city: str
    nickname: str
    conference: str
    division: str
    bref_abbreviation: str
    aliases: tuple[str, ...] = ()


def _normalize(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", folded.lower()).strip()


def normalize_team_alias(value: str) -> str:
    return _normalize(value)


TEAM_CATALOG: tuple[TeamCatalogEntry, ...] = (
    TeamCatalogEntry(
        UUID("b154a5db-abac-4bfe-84c0-490444d2b9a5"),
        "atlanta-hawks",
        "ATL",
        "Atlanta Hawks",
        "Atlanta",
        "Hawks",
        "East",
        "Southeast",
        "ATL",
        ("atlanta", "atlanta hawks"),
    ),
    TeamCatalogEntry(
        UUID("7927412c-868d-4650-b329-bdc07b20358c"),
        "boston-celtics",
        "BOS",
        "Boston Celtics",
        "Boston",
        "Celtics",
        "East",
        "Atlantic",
        "BOS",
        ("boston", "boston celtics"),
    ),
    TeamCatalogEntry(
        UUID("087804fc-096a-4432-b3cc-f20e5e37b1e7"),
        "brooklyn-nets",
        "BKN",
        "Brooklyn Nets",
        "Brooklyn",
        "Nets",
        "East",
        "Atlantic",
        "BRK",
        ("brooklyn", "brooklyn nets", "new jersey nets", "new jersey"),
    ),
    TeamCatalogEntry(
        UUID("c1ff54f0-83f2-4cbc-996d-abf7bda33c66"),
        "charlotte-hornets",
        "CHA",
        "Charlotte Hornets",
        "Charlotte",
        "Hornets",
        "East",
        "Southeast",
        "CHO",
        ("charlotte", "charlotte hornets", "charlotte bobcats"),
    ),
    TeamCatalogEntry(
        UUID("a96f53b4-0f5c-4cb6-8b88-21ba05224cae"),
        "chicago-bulls",
        "CHI",
        "Chicago Bulls",
        "Chicago",
        "Bulls",
        "East",
        "Central",
        "CHI",
        ("chicago", "chicago bulls"),
    ),
    TeamCatalogEntry(
        UUID("69ed0cf0-df80-4f50-bdeb-4101c2d592f5"),
        "cleveland-cavaliers",
        "CLE",
        "Cleveland Cavaliers",
        "Cleveland",
        "Cavaliers",
        "East",
        "Central",
        "CLE",
        ("cleveland", "cleveland cavaliers"),
    ),
    TeamCatalogEntry(
        UUID("a4ce9ddd-c621-4ccf-b7e5-95354cf42f25"),
        "dallas-mavericks",
        "DAL",
        "Dallas Mavericks",
        "Dallas",
        "Mavericks",
        "West",
        "Southwest",
        "DAL",
        ("dallas", "dallas mavericks"),
    ),
    TeamCatalogEntry(
        UUID("dee9acef-9d8a-4438-9a0d-fefcaf7cfe1a"),
        "denver-nuggets",
        "DEN",
        "Denver Nuggets",
        "Denver",
        "Nuggets",
        "West",
        "Northwest",
        "DEN",
        ("denver", "denver nuggets"),
    ),
    TeamCatalogEntry(
        UUID("df5b8036-7d77-44a4-80dc-fd39d7fd092b"),
        "detroit-pistons",
        "DET",
        "Detroit Pistons",
        "Detroit",
        "Pistons",
        "East",
        "Central",
        "DET",
        ("detroit", "detroit pistons", "fort wayne pistons"),
    ),
    TeamCatalogEntry(
        UUID("7bf8726a-a852-452d-b81f-14839127c5fb"),
        "golden-state-warriors",
        "GSW",
        "Golden State Warriors",
        "Golden State",
        "Warriors",
        "West",
        "Pacific",
        "GSW",
        ("golden state", "golden state warriors", "san francisco warriors"),
    ),
    TeamCatalogEntry(
        UUID("79f68dde-8f09-44c0-b908-b0c6e0df0410"),
        "houston-rockets",
        "HOU",
        "Houston Rockets",
        "Houston",
        "Rockets",
        "West",
        "Southwest",
        "HOU",
        ("houston", "houston rockets", "san diego rockets"),
    ),
    TeamCatalogEntry(
        UUID("a4fcbfee-d36c-40d1-be34-51e75aa925af"),
        "indiana-pacers",
        "IND",
        "Indiana Pacers",
        "Indiana",
        "Pacers",
        "East",
        "Central",
        "IND",
        ("indiana", "indiana pacers"),
    ),
    TeamCatalogEntry(
        UUID("a79dabb2-26c5-443c-bbb4-cabdd8db5958"),
        "los-angeles-clippers",
        "LAC",
        "Los Angeles Clippers",
        "Los Angeles",
        "Clippers",
        "West",
        "Pacific",
        "LAC",
        ("la clippers", "los angeles clippers", "buffalo braves", "san diego clippers"),
    ),
    TeamCatalogEntry(
        UUID("8cbd46d2-8092-4b1e-8b24-f31c7692cadd"),
        "los-angeles-lakers",
        "LAL",
        "Los Angeles Lakers",
        "Los Angeles",
        "Lakers",
        "West",
        "Pacific",
        "LAL",
        ("la lakers", "los angeles lakers", "minneapolis lakers"),
    ),
    TeamCatalogEntry(
        UUID("1036a395-f3a5-472e-b95f-ebe2e8202e9f"),
        "memphis-grizzlies",
        "MEM",
        "Memphis Grizzlies",
        "Memphis",
        "Grizzlies",
        "West",
        "Southwest",
        "MEM",
        ("memphis", "memphis grizzlies", "vancouver grizzlies"),
    ),
    TeamCatalogEntry(
        UUID("5d6c5618-db91-412a-ada6-96d11e73302f"),
        "miami-heat",
        "MIA",
        "Miami Heat",
        "Miami",
        "Heat",
        "East",
        "Southeast",
        "MIA",
        ("miami", "miami heat"),
    ),
    TeamCatalogEntry(
        UUID("2d787da9-01c7-4504-878e-8a5b0ec74609"),
        "milwaukee-bucks",
        "MIL",
        "Milwaukee Bucks",
        "Milwaukee",
        "Bucks",
        "East",
        "Central",
        "MIL",
        ("milwaukee", "milwaukee bucks"),
    ),
    TeamCatalogEntry(
        UUID("3cd9c269-597b-4eab-acb3-2d434f8b1280"),
        "minnesota-timberwolves",
        "MIN",
        "Minnesota Timberwolves",
        "Minnesota",
        "Timberwolves",
        "West",
        "Northwest",
        "MIN",
        ("minnesota", "minnesota timberwolves"),
    ),
    TeamCatalogEntry(
        UUID("79f6aacb-d37c-4132-8fce-dfbbcaa5bc5d"),
        "new-orleans-pelicans",
        "NOP",
        "New Orleans Pelicans",
        "New Orleans",
        "Pelicans",
        "West",
        "Southwest",
        "NOP",
        ("new orleans", "new orleans pelicans", "new orleans hornets"),
    ),
    TeamCatalogEntry(
        UUID("3cbdd44d-e2b2-458a-81cd-b3008d5ebb5b"),
        "new-york-knicks",
        "NYK",
        "New York Knicks",
        "New York",
        "Knicks",
        "East",
        "Atlantic",
        "NYK",
        ("new york", "new york knicks"),
    ),
    TeamCatalogEntry(
        UUID("bc007f7f-f88d-4699-8325-e2f5a3e32183"),
        "oklahoma-city-thunder",
        "OKC",
        "Oklahoma City Thunder",
        "Oklahoma City",
        "Thunder",
        "West",
        "Northwest",
        "OKC",
        ("oklahoma city", "oklahoma city thunder", "seattle supersonics", "seattle"),
    ),
    TeamCatalogEntry(
        UUID("afb5d7dd-df1e-47e0-b247-d1ace6475959"),
        "orlando-magic",
        "ORL",
        "Orlando Magic",
        "Orlando",
        "Magic",
        "East",
        "Southeast",
        "ORL",
        ("orlando", "orlando magic"),
    ),
    TeamCatalogEntry(
        UUID("8ea71a5c-0ade-41c4-8558-1e1f76990f9c"),
        "philadelphia-76ers",
        "PHI",
        "Philadelphia 76ers",
        "Philadelphia",
        "76ers",
        "East",
        "Atlantic",
        "PHI",
        ("philadelphia", "philadelphia 76ers", "syracuse nationals"),
    ),
    TeamCatalogEntry(
        UUID("811b221e-1e3e-4c60-ae9e-837b1572d757"),
        "phoenix-suns",
        "PHX",
        "Phoenix Suns",
        "Phoenix",
        "Suns",
        "West",
        "Pacific",
        "PHO",
        ("phoenix", "phoenix suns"),
    ),
    TeamCatalogEntry(
        UUID("250898d8-76ce-4f54-88de-ebcca751231d"),
        "portland-trail-blazers",
        "POR",
        "Portland Trail Blazers",
        "Portland",
        "Trail Blazers",
        "West",
        "Northwest",
        "POR",
        ("portland", "portland trail blazers"),
    ),
    TeamCatalogEntry(
        UUID("6d5835b4-ab01-42bc-a478-9cf95d39133b"),
        "sacramento-kings",
        "SAC",
        "Sacramento Kings",
        "Sacramento",
        "Kings",
        "West",
        "Pacific",
        "SAC",
        ("sacramento", "sacramento kings", "kansas city kings", "cincinnati royals"),
    ),
    TeamCatalogEntry(
        UUID("1a24da7b-0a03-4b6a-a230-5732dbeb9d96"),
        "san-antonio-spurs",
        "SAS",
        "San Antonio Spurs",
        "San Antonio",
        "Spurs",
        "West",
        "Southwest",
        "SAS",
        ("san antonio", "san antonio spurs"),
    ),
    TeamCatalogEntry(
        UUID("8f941860-dc83-4289-8ed8-7ea9417d53b8"),
        "toronto-raptors",
        "TOR",
        "Toronto Raptors",
        "Toronto",
        "Raptors",
        "East",
        "Atlantic",
        "TOR",
        ("toronto", "toronto raptors"),
    ),
    TeamCatalogEntry(
        UUID("241af2e1-5322-427d-a549-9b318bba9cbf"),
        "utah-jazz",
        "UTA",
        "Utah Jazz",
        "Utah",
        "Jazz",
        "West",
        "Northwest",
        "UTA",
        ("utah", "utah jazz", "new orleans jazz"),
    ),
    TeamCatalogEntry(
        UUID("9094a6ee-648a-494a-8c30-bf303c22ceb6"),
        "washington-wizards",
        "WAS",
        "Washington Wizards",
        "Washington",
        "Wizards",
        "East",
        "Southeast",
        "WAS",
        ("washington", "washington wizards", "washington bullets", "bullets"),
    ),
)


_BY_ALIAS: dict[str, TeamCatalogEntry] = {}
for _entry in TEAM_CATALOG:
    for _alias in (
        _entry.abbreviation,
        _entry.bref_abbreviation,
        _entry.canonical_slug,
        _entry.full_name,
        *_entry.aliases,
    ):
        _key = normalize_team_alias(_alias)
        if _key in _BY_ALIAS and _BY_ALIAS[_key].team_id != _entry.team_id:
            raise RuntimeError(f"duplicate team catalog alias: {_alias}")
        _BY_ALIAS[_key] = _entry


def team_by_alias(value: str) -> TeamCatalogEntry | None:
    return _BY_ALIAS.get(normalize_team_alias(value))


def validate_catalog() -> None:
    ids = [entry.team_id for entry in TEAM_CATALOG]
    slugs = [entry.canonical_slug for entry in TEAM_CATALOG]
    bref = [entry.bref_abbreviation for entry in TEAM_CATALOG]
    if len(ids) != len(set(ids)) or len(slugs) != len(set(slugs)) or len(bref) != len(set(bref)):
        raise RuntimeError("team catalog contains duplicate canonical values")


validate_catalog()

__all__ = [
    "TEAM_CATALOG",
    "TeamCatalogEntry",
    "normalize_team_alias",
    "team_by_alias",
    "validate_catalog",
]
