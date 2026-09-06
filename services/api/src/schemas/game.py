from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ScheduledGame(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    game_id: str
    season: str
    season_type: str | None = None
    game_date: date
    status: str
    arena: str | None = None
    arena_city: str | None = None
    arena_state: str | None = None
    home_team_id: int
    home_team_abbreviation: str | None = None
    home_team_name: str | None = None
    away_team_id: int
    away_team_abbreviation: str | None = None
    away_team_name: str | None = None


class GameResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    game_id: str
    season: str
    season_type: str | None = None
    game_date: date
    arena: str | None = None
    arena_city: str | None = None
    arena_state: str | None = None
    home_team_id: int
    home_team_abbreviation: str | None = None
    home_team_name: str | None = None
    home_score: int | None = None
    away_team_id: int
    away_team_abbreviation: str | None = None
    away_team_name: str | None = None
    away_score: int | None = None
    winning_team_id: int | None = None
    winner_location: str | None = None
    score_margin: int | None = None


class PlayByPlayEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    game_id: str
    action_number: int
    period: int | None = None
    clock: str | None = None
    clock_remaining_seconds: float | None = None
    elapsed_seconds: float
    score_home: int
    score_away: int
    score_differential: int
    home_points: int | None = None
    away_points: int | None = None
    points_scored: int | None = None
    scoring_side: str | None = None
    team_id: int | None = None
    player_id: int | None = None
    action_type: str | None = None
    sub_type: str | None = None
    description: str | None = None


class GameFlow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    game_id: str
    season: str
    game_date: date
    home_team_id: int
    home_team_abbreviation: str | None = None
    home_team_name: str | None = None
    home_primary_color: str | None = None
    home_alternate_color: str | None = None
    home_score: int | None = None
    away_team_id: int
    away_team_abbreviation: str | None = None
    away_team_name: str | None = None
    away_primary_color: str | None = None
    away_alternate_color: str | None = None
    away_score: int | None = None
    winning_team_id: int | None = None
    winning_team_abbreviation: str | None = None
    winner_location: str | None = None
    has_play_by_play: bool = False
    scoring_play_count: int | None = None
    max_home_lead: int | None = None
    max_away_lead: int | None = None
    max_lead: int | None = None
    lead_changes: int | None = None
    ties: int | None = None
    home_lead_seconds: float | None = None
    away_lead_seconds: float | None = None
    tied_seconds: float | None = None
    home_lead_pct: float | None = None
    away_lead_pct: float | None = None
    tied_pct: float | None = None
    game_elapsed_seconds: float | None = None
    biggest_run_team_abbreviation: str | None = None
    biggest_run_winner_points: int | None = None
    biggest_run_opponent_points: int | None = None
    biggest_run_start_seconds: float | None = None
    biggest_run_end_seconds: float | None = None
    biggest_run_label: str | None = None


class TeamGameResult(GameResult):
    location: str
    opponent_team_id: int
    opponent_abbreviation: str | None = None
    opponent_name: str | None = None
    team_score: int | None = None
    opponent_score: int | None = None
    is_win: bool | None = None


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    season: str | None = None


class QueryResponse(BaseModel):
    answer: str
    data: list = Field(default_factory=list)
    sql: str | None = None
