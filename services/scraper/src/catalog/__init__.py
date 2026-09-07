"""Repo-owned canonical catalogs used by provider adapters."""

from catalog.teams import TEAM_CATALOG, TeamCatalogEntry, normalize_team_alias, team_by_alias

__all__ = ["TEAM_CATALOG", "TeamCatalogEntry", "normalize_team_alias", "team_by_alias"]
