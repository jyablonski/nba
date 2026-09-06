from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


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
