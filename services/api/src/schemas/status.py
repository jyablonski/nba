from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, field_serializer


class WarehouseStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    last_scraped_at: datetime | None = None
    # From the hand-maintained source.scrape_pipeline.daily_refresh_utc. Null
    # when no schedule is recorded — the UI must hide the stamp, not guess.
    next_scrape_at: datetime | None = None
    player_count: int = 0
    game_count: int = 0
    season_count: int = 0
    first_season: str | None = None
    last_season: str | None = None

    @field_serializer("last_scraped_at", "next_scrape_at", when_used="json")
    def serialize_timestamps(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return aware.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
