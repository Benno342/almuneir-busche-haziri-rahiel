"""The Alembic migrations and the ORM models must describe the same schema."""

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine, inspect

from padel.infrastructure.db.models import Base
from tests.db import downgrade_to_base, migrate


def _diff(engine: Engine) -> list[object]:
    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        return list(compare_metadata(context, Base.metadata))


def test_models_match_migrations_sqlite(sqlite_engine: Engine) -> None:
    assert _diff(sqlite_engine) == []


@pytest.mark.integration
def test_models_match_migrations_postgres(postgres_engine: Engine) -> None:
    assert _diff(postgres_engine) == []


def test_downgrade_and_upgrade_roundtrip(sqlite_engine: Engine) -> None:
    downgrade_to_base(sqlite_engine)
    assert set(inspect(sqlite_engine).get_table_names()) == {"alembic_version"}
    migrate(sqlite_engine)
    assert "bookings" in inspect(sqlite_engine).get_table_names()
