import pytest

from config import Settings, get_settings


@pytest.mark.unit
def test_sqlalchemy_url_from_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://nba_user:nba_pass@db:5432/nba")
    settings = Settings()
    assert settings.sqlalchemy_url == "postgresql://nba_user:nba_pass@db:5432/nba"


@pytest.mark.unit
def test_sqlalchemy_url_from_parts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(
        postgres_host="pg",
        postgres_port=6543,
        postgres_db="stats",
        postgres_user="u",
        postgres_password="p",
        database_url=None,
    )
    assert settings.sqlalchemy_url == "postgresql://u:p@pg:6543/stats"


@pytest.mark.unit
def test_nlp_backend_defaults_to_rules() -> None:
    assert Settings.model_fields["nlp_backend"].default == "rules"
    assert Settings.model_fields["nlp_llm_api_key"].default is None
    assert Settings.model_fields["cube_api_url"].default is None


@pytest.mark.unit
def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    first = get_settings()
    second = get_settings()
    assert first is second
    get_settings.cache_clear()
