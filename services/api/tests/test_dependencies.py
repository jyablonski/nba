from unittest.mock import MagicMock

import pytest

from dependencies import get_cube_analytics, get_cube_client, get_db


@pytest.mark.unit
def test_get_db_closes_session(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    monkeypatch.setattr("dependencies.SessionLocal", lambda: session)
    generator = get_db()
    assert next(generator) is session
    generator.close()
    session.close.assert_called_once()


@pytest.mark.unit
def test_cube_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    from config import Settings

    settings = Settings(cube_api_url="http://cube:4000", cubejs_api_secret="s")
    client = get_cube_client(settings)
    assert client.base_url == "http://cube:4000"
    analytics = get_cube_analytics(client)
    assert analytics.client is client
