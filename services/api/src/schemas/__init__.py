from pydantic import BaseModel, Field

from schemas.game import (
    GameCollapse,
    GameFlow,
    GameResult,
    PlayByPlayEvent,
    QueryRequest,
    QueryResponse,
    ScheduledGame,
    TeamGameResult,
)
from schemas.player import (
    BackToBackStats,
    GameLogEntry,
    HeadToHeadComparison,
    PlayerComparison,
    PlayerDetail,
    PlayerSeasonStats,
    PlayerSummary,
)
from schemas.standing import StandingRow, StandingSummary
from schemas.status import WarehouseStatus
from schemas.team import TeamDetail, TeamRecord, TeamSummary


class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int


class PaginatedResponse[T](BaseModel):
    data: list[T]
    meta: PaginationMeta


class ItemResponse[T](BaseModel):
    data: T


class SeasonListResponse(BaseModel):
    data: list[str]
    meta: PaginationMeta = Field(default_factory=lambda: PaginationMeta(total=0, limit=0, offset=0))


__all__ = [
    "BackToBackStats",
    "GameLogEntry",
    "HeadToHeadComparison",
    "GameCollapse",
    "GameFlow",
    "GameResult",
    "ItemResponse",
    "PlayByPlayEvent",
    "PaginatedResponse",
    "PaginationMeta",
    "PlayerComparison",
    "PlayerDetail",
    "PlayerSeasonStats",
    "PlayerSummary",
    "WarehouseStatus",
    "QueryRequest",
    "QueryResponse",
    "ScheduledGame",
    "SeasonListResponse",
    "StandingRow",
    "StandingSummary",
    "TeamDetail",
    "TeamGameResult",
    "TeamRecord",
    "TeamSummary",
]
