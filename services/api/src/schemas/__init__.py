from pydantic import BaseModel, Field

from schemas.admin import (
    AdminHealth,
    AdminJob,
    DbtStatus,
    GoldTable,
    JobRequest,
    JobType,
    ModelStatus,
    PipelineGate,
    PipelineRun,
    SourceHealth,
    TableFreshness,
)
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
    "AdminHealth",
    "AdminJob",
    "BackToBackStats",
    "DbtStatus",
    "GameCollapse",
    "GameFlow",
    "GameLogEntry",
    "GameResult",
    "GoldTable",
    "HeadToHeadComparison",
    "ItemResponse",
    "JobRequest",
    "JobType",
    "ModelStatus",
    "PaginatedResponse",
    "PaginationMeta",
    "PipelineGate",
    "PipelineRun",
    "PlayByPlayEvent",
    "PlayerComparison",
    "PlayerDetail",
    "PlayerSeasonStats",
    "PlayerSummary",
    "QueryRequest",
    "QueryResponse",
    "ScheduledGame",
    "SeasonListResponse",
    "SourceHealth",
    "StandingRow",
    "StandingSummary",
    "TableFreshness",
    "TeamDetail",
    "TeamGameResult",
    "TeamRecord",
    "TeamSummary",
    "WarehouseStatus",
]
