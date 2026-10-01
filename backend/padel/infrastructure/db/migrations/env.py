"""Alembic environment.

URL resolution order: an explicitly passed connection (tests), the `sqlalchemy.url`
option set programmatically, then the DATABASE_URL environment variable.
"""

from alembic import context

from padel.infrastructure.db.models import Base
from padel.infrastructure.db.session import create_db_engine, database_url_from_env

config = context.config
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url") or database_url_from_env(),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return
    engine = create_db_engine(config.get_main_option("sqlalchemy.url") or database_url_from_env())
    with engine.connect() as connection:
        _run(connection)


def _run(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # SQLite cannot ALTER most things; batch mode recreates tables instead.
        render_as_batch=connection.dialect.name == "sqlite",
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
