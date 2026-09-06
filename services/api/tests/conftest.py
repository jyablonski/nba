from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from dependencies import get_cube_analytics, get_db
from main import create_app

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.postgres_tc import (  # noqa: E402
    bootstrap_engine,
    docker_available,
    start_postgres_container,
)


class MappingRow:
    def __init__(self, data: dict):
        self._mapping = data

    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self._mapping.values())[key]
        return self._mapping[key]

    def keys(self):
        return self._mapping.keys()

    def values(self):
        return self._mapping.values()

    def items(self):
        return self._mapping.items()

    def __iter__(self):
        return iter(self._mapping)

    def __len__(self):
        return len(self._mapping)


class QueryResult:
    def __init__(self, rows=None, scalar=None):
        self._rows = list(rows or [])
        self._scalar = scalar

    def first(self):
        return self._rows[0] if self._rows else None

    def mappings(self):
        return self

    def scalar_one(self):
        if self._scalar is not None:
            return self._scalar
        return 0

    def scalar(self):
        return self._scalar

    def one(self):
        return self._rows[0]

    def __iter__(self):
        return iter(self._rows)


class ScriptedSession:
    def __init__(self) -> None:
        self.queue: list[QueryResult] = []
        self.closed = False

    def execute(self, stmt, params=None):
        if not self.queue:
            raise AssertionError(f"Unexpected SQL execute: {stmt} {params}")
        return self.queue.pop(0)

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def session() -> ScriptedSession:
    return ScriptedSession()


@pytest.fixture
def mapping_row():
    return MappingRow


@pytest.fixture
def query_result():
    return QueryResult


@pytest.fixture
def cube_analytics():
    from test_nl_eval import FakeCubeAnalytics

    return FakeCubeAnalytics()


@pytest.fixture
def client(session: ScriptedSession, cube_analytics) -> TestClient:
    app = create_app()

    def override_db():
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_cube_analytics] = lambda: cube_analytics
    return TestClient(app)


@pytest.fixture(scope="session")
def postgres_engine():
    if not docker_available():
        pytest.skip("Docker is not available for Testcontainers Postgres")
    container, url = start_postgres_container()
    engine = bootstrap_engine(
        url,
        with_gold_schema=True,
        with_gold_seed=True,
    )
    try:
        yield engine
    finally:
        engine.dispose()
        container.stop()


@pytest.fixture(scope="session")
def database_url(postgres_engine) -> str:
    return str(postgres_engine.url)


@pytest.fixture
def integration_client(postgres_engine) -> TestClient:
    SessionLocal = sessionmaker(
        bind=postgres_engine,
        autocommit=False,
        autoflush=False,
    )
    app = create_app()

    def override_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)
