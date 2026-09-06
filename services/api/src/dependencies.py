from collections.abc import Generator

from cube.analytics import CubeAnalytics
from cube.client import CubeClient
from fastapi import Depends
from sqlalchemy.orm import Session

from config import Settings, get_settings
from db import SessionLocal
from repositories.games import GamesRepository
from repositories.players import PlayersRepository
from repositories.standings import StandingsRepository
from repositories.status import StatusRepository
from repositories.teams import TeamsRepository


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_players_repository(db: Session = Depends(get_db)) -> PlayersRepository:
    return PlayersRepository(db)


def get_teams_repository(db: Session = Depends(get_db)) -> TeamsRepository:
    return TeamsRepository(db)


def get_games_repository(db: Session = Depends(get_db)) -> GamesRepository:
    return GamesRepository(db)


def get_standings_repository(db: Session = Depends(get_db)) -> StandingsRepository:
    return StandingsRepository(db)


def get_status_repository(db: Session = Depends(get_db)) -> StatusRepository:
    return StatusRepository(db)


def get_cube_client(settings: Settings = Depends(get_settings)) -> CubeClient:
    return CubeClient(settings.cube_api_url, settings.cubejs_api_secret)


def get_cube_analytics(
    client: CubeClient = Depends(get_cube_client),
) -> CubeAnalytics:
    return CubeAnalytics(client)
