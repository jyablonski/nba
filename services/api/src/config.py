from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    database_url: str | None = None
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "nba"
    postgres_user: str = "nba_user"
    postgres_password: str = "nba_pass"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    nlp_backend: Literal["rules", "llm"] = "rules"
    nlp_llm_api_key: str | None = None
    nlp_llm_base_url: str = "https://api.openai.com/v1"
    nlp_llm_model: str = "gpt-4o-mini"
    cube_api_url: str | None = None
    cubejs_api_secret: str | None = None

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
