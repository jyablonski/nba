from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.postgres_tc import (  # noqa: E402
    bootstrap_engine,
    docker_available,
    start_postgres_container,
)


@pytest.fixture(scope="session")
def postgres_engine() -> Iterator[Engine]:
    if not docker_available():
        pytest.skip("Docker is not available for Testcontainers Postgres")
    container, url = start_postgres_container()
    engine = bootstrap_engine(url)
    try:
        yield engine
    finally:
        engine.dispose()
        container.stop()


@pytest.fixture(scope="session")
def database_url(postgres_engine: Engine) -> str:
    return postgres_engine.url.render_as_string(hide_password=False)


@pytest.fixture
def db_session_factory(postgres_engine: Engine, monkeypatch: pytest.MonkeyPatch):
    factory = sessionmaker(bind=postgres_engine, autoflush=False, autocommit=False)
    monkeypatch.setattr("db.SessionLocal", factory)
    return factory


@pytest.fixture
def db_session(db_session_factory) -> Iterator[Session]:
    session = db_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
