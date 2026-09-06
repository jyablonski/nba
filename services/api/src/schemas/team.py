from pydantic import BaseModel, ConfigDict, Field

from schemas.standing import StandingSummary


class TeamSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    team_id: int
    abbreviation: str
    team_name: str
    conference: str
    division: str
    city: str | None = None
    nickname: str | None = None
    wins: int | None = None
    losses: int | None = None
    win_pct: float | None = None
    record_source: str | None = None
    pts_scored_avg: float | None = None
    pts_allowed_avg: float | None = None


class TeamRecord(BaseModel):
    team_id: int
    team_name: str
    wins: int
    losses: int
    win_pct: float
    games: int
    filters_applied: dict = Field(default_factory=dict)


class TeamDetail(TeamSummary):
    arena_name: str | None = None
    arena_latitude: float | None = None
    arena_longitude: float | None = None
    primary_color: str | None = None
    alternate_color: str | None = None
    current_season_payroll: int | None = None
    current_remaining_guaranteed: int | None = None
    current_contract_season: str | None = None
    salary_cap: int | None = None
    luxury_tax: int | None = None
    first_apron: int | None = None
    second_apron: int | None = None
    over_luxury_tax: bool | None = None
    over_first_apron: bool | None = None
    over_second_apron: bool | None = None
    record_season: str | None = None
    season_record: TeamRecord | None = None
    play_in_record: TeamRecord | None = None
    playoff_record: TeamRecord | None = None
    standing: StandingSummary | None = None
