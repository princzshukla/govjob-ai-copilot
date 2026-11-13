"""Alembic environment (async).

The database URL comes from the application settings (env driven, identical to
the API process) so migrations and the app can never point at different
databases. Importing ``app.core.database`` also imports every model module,
which is what populates ``Base.metadata`` for autogenerate.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.database import Base, db_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# NOTE: pass the URL directly (offline) or via create_async_engine (online).
# Do NOT do config.set_main_option("sqlalchemy.url", db_url) — it goes through
# configparser, which rejects URLs whose password contains % (percent-encoded
# "@" and friends). The password in the Postgres URL comes pre-encoded, and
# the parser treats "%" as a variable interpolation marker and crashes.

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a DBAPI connection (emit SQL only)."""
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    # NullPool: a migration run is short lived and must not leave pooled
    # asyncpg connections bound to a closing event loop.
    connectable = create_async_engine(db_url, poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
