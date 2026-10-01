"""Engine and session setup."""

import os
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_DATABASE_URL = "sqlite:///./padel.db"


def normalize_database_url(url: str) -> str:
    """Render hands out `postgres://...`; SQLAlchemy needs an explicit driver."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url.removeprefix(prefix)
    return url


def database_url_from_env() -> str:
    return normalize_database_url(os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))


def create_db_engine(url: str) -> Engine:
    url = normalize_database_url(url)
    engine = create_engine(url)
    if engine.dialect.name == "sqlite":
        _make_sqlite_behave(engine)
    return engine


def _make_sqlite_behave(engine: Engine) -> None:
    """SQLite differs from PostgreSQL out of the box:

    - foreign keys are only enforced with PRAGMA foreign_keys=ON
    - pysqlite's implicit transaction handling breaks SAVEPOINTs (begin_nested), which
      the repositories use; the recipe below is the one from the SQLAlchemy docs.
    """

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_connection: Any, _record: Any) -> None:
        dbapi_connection.isolation_level = None
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    @event.listens_for(engine, "begin")
    def _on_begin(connection: Any) -> None:
        connection.exec_driver_sql("BEGIN")


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
