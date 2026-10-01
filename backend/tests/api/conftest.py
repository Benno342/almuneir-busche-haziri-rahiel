from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from padel.application.repositories import Repositories
from padel.infrastructure.db.repositories import sql_repositories
from padel.infrastructure.db.session import create_session_factory
from padel.interfaces.api.main import create_app
from tests.conftest import open_session
from tests.fakes import FakeClock

Seed = Callable[[], AbstractContextManager[Repositories]]


@pytest.fixture
def client(sqlite_engine: Engine, clock: FakeClock) -> Iterator[TestClient]:
    """API wired to a migrated SQLite DB and the FakeClock (no lifespan, no env vars)."""
    app = create_app(session_factory=create_session_factory(sqlite_engine), clock=clock)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def seed(sqlite_engine: Engine) -> Seed:
    """`with seed() as repos: ...` inserts test data and commits it at the end."""

    @contextmanager
    def _seed() -> Iterator[Repositories]:
        with open_session(sqlite_engine) as session:
            yield sql_repositories(session)
            session.commit()

    return _seed
