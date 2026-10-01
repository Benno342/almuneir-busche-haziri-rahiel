import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from padel.application.repositories import Repositories
from padel.infrastructure.db.session import create_db_engine, create_session_factory
from tests.builders import DEFAULT_NOW
from tests.db import downgrade_to_base, migrate, truncate_all
from tests.fakes import FakeClock, in_memory_repositories


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(DEFAULT_NOW)


@pytest.fixture
def fake_repos() -> Repositories:
    return in_memory_repositories()


# --- SQL databases --------------------------------------------------------------------
# SQLite: a fresh migrated file per test (fast, runs in the unit job).
# PostgreSQL: TEST_DATABASE_URL, migrated once per run and truncated before every test
# (integration job / docker compose). Tests needing it are skipped when it is unset.


@pytest.fixture
def sqlite_engine(tmp_path: Path) -> Iterator[Engine]:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'test.db'}")
    migrate(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def _postgres_engine_once() -> Iterator[Engine]:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set (start Postgres via docker compose)")
    engine = create_db_engine(url)
    downgrade_to_base(engine)
    migrate(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def postgres_engine(_postgres_engine_once: Engine) -> Engine:
    truncate_all(_postgres_engine_once)
    return _postgres_engine_once


@contextmanager
def open_session(engine: Engine) -> Iterator[Session]:
    session = create_session_factory(engine)()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
