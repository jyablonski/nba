from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, field_serializer


class WarehouseStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    last_scraped_at: datetime | None = None
    player_count: int = 0
    game_count: int = 0
    season_count: int = 0
    first_season: str | None = None
    last_season: str | None = None

    @field_serializer("last_scraped_at", when_used="json")
    def serialize_last_scraped_at(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return aware.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
