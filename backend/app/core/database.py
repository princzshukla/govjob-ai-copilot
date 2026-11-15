from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
# Re-exported for alembic/env.py (target_metadata); not used by the app itself.
from app.models.exam import Base

# Model imports so metadata knows about all tables
import app.models.adaptive  # noqa: F401
import app.models.auth  # noqa: F401
import app.models.candidate  # noqa: F401
import app.models.exam  # noqa: F401
import app.models.progress  # noqa: F401
import app.models.report  # noqa: F401
import app.models.roadmap  # noqa: F401
import app.models.telegram  # noqa: F401

db_url = str(settings.DATABASE_URL)
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql+psycopg://"):
    db_url = db_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)

# Transaction-mode poolers (Supabase pgbouncer on :6543, any pgbouncer
# host) swap the underlying Postgres connection between statements, so an
# asyncpg per-connection prepared-statement cache collides and the request
# crashes with a 500. Route handlers then escape every middleware, the 500
# goes out without CORS headers and the browser reports `Failed to fetch`.
_POOLER_MARKERS = (":6543", "pooler.supabase.com", "pgbouncer", "pooler.")
_is_transaction_pooler = any(marker in db_url.lower() for marker in _POOLER_MARKERS)

_engine_kwargs = {
    "echo": False,
    "connect_args": {},
}
if settings.ENVIRONMENT == "test":
    # Prepared-statement caching breaks across per-test loops; keep it off.
    _engine_kwargs["connect_args"] = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "server_settings": {"lock_timeout": "5000"},
    }
elif _is_transaction_pooler:
    # Poolers may not reuse a backend connection, so cached prepared
    # statements belong to a different session than the next lookup expects.
    _engine_kwargs["connect_args"] = {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }
if settings.ENVIRONMENT == "test":
    engine = create_async_engine(db_url, poolclass=NullPool, **_engine_kwargs)
else:
    engine = create_async_engine(
        db_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        **_engine_kwargs,
    )

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
