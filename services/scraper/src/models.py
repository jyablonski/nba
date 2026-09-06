from datetime import date, datetime

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Player(Base):
    __tablename__ = "players"
    __table_args__ = {"schema": "source"}

    player_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    jersey_number: Mapped[str | None] = mapped_column(String(10))
    position: Mapped[str | None] = mapped_column(String(20))
    height: Mapped[str | None] = mapped_column(String(10))
    weight: Mapped[int | None] = mapped_column(Integer)
    birth_date: Mapped[date | None] = mapped_column(Date)
    team_id: Mapped[int | None] = mapped_column(Integer)
    from_year: Mapped[int | None] = mapped_column(Integer)
    to_year: Mapped[int | None] = mapped_column(Integer)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = {"schema": "source"}

    team_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    abbreviation: Mapped[str] = mapped_column(String(5), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(50), nullable=False)
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    conference: Mapped[str] = mapped_column(String(10), nullable=False)
    division: Mapped[str] = mapped_column(String(20), nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class Game(Base):
    __tablename__ = "games"
    __table_args__ = {"schema": "source"}

    game_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    season: Mapped[str] = mapped_column(String(10), nullable=False)
    season_type: Mapped[str] = mapped_column(String(20), nullable=False)
    game_date: Mapped[date] = mapped_column(Date, nullable=False)
    home_team_id: Mapped[int] = mapped_column(Integer, nullable=False)
    away_team_id: Mapped[int] = mapped_column(Integer, nullable=False)
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    arena: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(50))
    state: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Final")
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class PlayerGameLog(Base):
    __tablename__ = "player_game_logs"
    __table_args__ = (
        UniqueConstraint("player_id", "game_id", name="player_game_logs_player_id_game_id_key"),
        {"schema": "source"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(Integer, nullable=False)
    game_id: Mapped[str] = mapped_column(String(20), nullable=False)
    team_id: Mapped[int] = mapped_column(Integer, nullable=False)
    game_date: Mapped[date] = mapped_column(Date, nullable=False)
    season: Mapped[str] = mapped_column(String(10), nullable=False)
    matchup: Mapped[str] = mapped_column(String(20), nullable=False)
    wl: Mapped[str | None] = mapped_column(CHAR(1))
    min: Mapped[float | None] = mapped_column(Float)
    pts: Mapped[int | None] = mapped_column(Integer)
    reb: Mapped[int | None] = mapped_column(Integer)
    ast: Mapped[int | None] = mapped_column(Integer)
    stl: Mapped[int | None] = mapped_column(Integer)
    blk: Mapped[int | None] = mapped_column(Integer)
    tov: Mapped[int | None] = mapped_column(Integer)
    fgm: Mapped[int | None] = mapped_column(Integer)
    fga: Mapped[int | None] = mapped_column(Integer)
    fg_pct: Mapped[float | None] = mapped_column(Float)
    fg3m: Mapped[int | None] = mapped_column(Integer)
    fg3a: Mapped[int | None] = mapped_column(Integer)
    fg3_pct: Mapped[float | None] = mapped_column(Float)
    ftm: Mapped[int | None] = mapped_column(Integer)
    fta: Mapped[int | None] = mapped_column(Integer)
    ft_pct: Mapped[float | None] = mapped_column(Float)
    plus_minus: Mapped[int | None] = mapped_column(Integer)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class PlayerContract(Base):
    __tablename__ = "player_contracts"
    __table_args__ = (
        UniqueConstraint(
            "bref_player_slug",
            "bref_team_abbreviation",
            "season",
            name="player_contracts_bref_player_slug_bref_team_abbreviation_season_key",
        ),
        {"schema": "source"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bref_player_slug: Mapped[str] = mapped_column(String(32), nullable=False)
    player_name: Mapped[str] = mapped_column(String(200), nullable=False)
    player_name_normalized: Mapped[str] = mapped_column(String(200), nullable=False)
    bref_team_abbreviation: Mapped[str] = mapped_column(String(5), nullable=False)
    nba_team_abbreviation: Mapped[str] = mapped_column(String(5), nullable=False)
    season: Mapped[str] = mapped_column(String(10), nullable=False)
    salary: Mapped[int | None] = mapped_column(BigInteger)
    is_fully_guaranteed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    remaining_guaranteed: Mapped[int | None] = mapped_column(BigInteger)
    player_age: Mapped[int | None] = mapped_column(Integer)
    source_url: Mapped[str] = mapped_column(String(300), nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class Standing(Base):
    __tablename__ = "standings"
    __table_args__ = (
        UniqueConstraint(
            "season",
            "season_type",
            "team_id",
            name="standings_season_season_type_team_id_key",
        ),
        {"schema": "source"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(Integer, nullable=False)
    season: Mapped[str] = mapped_column(String(10), nullable=False)
    season_type: Mapped[str] = mapped_column(String(20), nullable=False, default="Regular Season")
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    conference: Mapped[str | None] = mapped_column(String(10))
    division: Mapped[str | None] = mapped_column(String(20))
    conference_rank: Mapped[int | None] = mapped_column(Integer)
    division_rank: Mapped[int | None] = mapped_column(Integer)
    wins: Mapped[int | None] = mapped_column(Integer)
    losses: Mapped[int | None] = mapped_column(Integer)
    win_pct: Mapped[float | None] = mapped_column(Float)
    games_back: Mapped[float | None] = mapped_column(Float)
    conf_games_back: Mapped[float | None] = mapped_column(Float)
    streak: Mapped[str | None] = mapped_column(String(20))
    last_10: Mapped[str | None] = mapped_column(String(10))
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class PlayerInjury(Base):
    __tablename__ = "player_injuries"
    __table_args__ = (
        UniqueConstraint(
            "player_name_normalized",
            "bref_team_abbreviation",
            name="player_injuries_player_name_normalized_bref_team_abbreviation_key",
        ),
        {"schema": "source"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_name: Mapped[str] = mapped_column(String(200), nullable=False)
    player_name_normalized: Mapped[str] = mapped_column(String(200), nullable=False)
    bref_player_slug: Mapped[str | None] = mapped_column(String(32))
    bref_team_abbreviation: Mapped[str] = mapped_column(String(5), nullable=False)
    nba_team_abbreviation: Mapped[str] = mapped_column(String(5), nullable=False)
    update_date: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str] = mapped_column(String(300), nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class GameOdds(Base):
    __tablename__ = "game_odds"
    __table_args__ = (
        UniqueConstraint(
            "odds_event_id",
            "bookmaker",
            "market",
            name="game_odds_odds_event_id_bookmaker_market_key",
        ),
        {"schema": "source"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    odds_event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    commence_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    home_team_name: Mapped[str] = mapped_column(String(100), nullable=False)
    away_team_name: Mapped[str] = mapped_column(String(100), nullable=False)
    game_id: Mapped[str | None] = mapped_column(String(20))
    bookmaker: Mapped[str] = mapped_column(String(50), nullable=False)
    market: Mapped[str] = mapped_column(String(20), nullable=False)
    home_price: Mapped[int | None] = mapped_column(Integer)
    away_price: Mapped[int | None] = mapped_column(Integer)
    home_implied_wp: Mapped[float | None] = mapped_column(Float)
    away_implied_wp: Mapped[float | None] = mapped_column(Float)
    home_market_wp: Mapped[float | None] = mapped_column(Float)
    away_market_wp: Mapped[float | None] = mapped_column(Float)
    spread_home: Mapped[float | None] = mapped_column(Float)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class GamePrediction(Base):
    __tablename__ = "game_predictions"
    __table_args__ = (
        UniqueConstraint(
            "game_id",
            "as_of",
            "model_version",
            name="game_predictions_game_id_as_of_model_version_key",
        ),
        {"schema": "source"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(String(20), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    home_team_id: Mapped[int] = mapped_column(Integer, nullable=False)
    away_team_id: Mapped[int] = mapped_column(Integer, nullable=False)
    model_wp: Mapped[float] = mapped_column(Float, nullable=False)
    market_wp: Mapped[float | None] = mapped_column(Float)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class PlayByPlay(Base):
    __tablename__ = "play_by_play"
    __table_args__ = (
        UniqueConstraint(
            "game_id",
            "action_number",
            "action_id",
            name="play_by_play_game_id_action_number_action_id_key",
        ),
        {"schema": "source"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(String(20), nullable=False)
    season: Mapped[str] = mapped_column(String(10), nullable=False)
    action_number: Mapped[int] = mapped_column(Integer, nullable=False)
    action_id: Mapped[int | None] = mapped_column(Integer)
    period: Mapped[int | None] = mapped_column(Integer)
    clock: Mapped[str | None] = mapped_column(String(32))
    score_home: Mapped[int | None] = mapped_column(Integer)
    score_away: Mapped[int | None] = mapped_column(Integer)
    team_id: Mapped[int | None] = mapped_column(Integer)
    player_id: Mapped[int | None] = mapped_column(Integer)
    action_type: Mapped[str | None] = mapped_column(String(50))
    sub_type: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(String)
    extras: Mapped[dict | None] = mapped_column(JSONB)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class RedditPost(Base):
    __tablename__ = "reddit_posts"
    __table_args__ = {"schema": "source"}

    reddit_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    subreddit: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    author: Mapped[str | None] = mapped_column(String(50))
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    num_comments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    permalink: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str | None] = mapped_column(String)
    selftext: Mapped[str | None] = mapped_column(String)
    flair: Mapped[str | None] = mapped_column(String(200))
    is_self: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class RedditComment(Base):
    __tablename__ = "reddit_comments"
    __table_args__ = {"schema": "source"}

    reddit_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    post_reddit_id: Mapped[str] = mapped_column(String(16), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String(20))
    author: Mapped[str | None] = mapped_column(String(50))
    body: Mapped[str | None] = mapped_column(String)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    permalink: Mapped[str] = mapped_column(String(500), nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class TeamPayroll(Base):
    __tablename__ = "team_payroll"
    __table_args__ = (
        UniqueConstraint(
            "bref_team_abbreviation",
            "season",
            name="team_payroll_bref_team_abbreviation_season_key",
        ),
        {"schema": "source"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bref_team_abbreviation: Mapped[str] = mapped_column(String(5), nullable=False)
    nba_team_abbreviation: Mapped[str] = mapped_column(String(5), nullable=False)
    season: Mapped[str] = mapped_column(String(10), nullable=False)
    total_salary: Mapped[int | None] = mapped_column(BigInteger)
    remaining_guaranteed: Mapped[int | None] = mapped_column(BigInteger)
    source_url: Mapped[str] = mapped_column(String(300), nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
