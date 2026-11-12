from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models.exam import Base

# Model imports so metadata knows about all tables
import app.models.adaptive  # noqa: F401
import app.models.auth  # noqa: F401
import app.models.candidate  # noqa: F401
import app.models.exam  # noqa: F401
import app.models.roadmap  # noqa: F401
import app.models.syllabus  # noqa: F401

db_url = str(settings.DATABASE_URL)
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql+psycopg://"):
    db_url = db_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)

# Tests run each case in a fresh event loop and asyncpg connections are
# loop-bound, so pooling is disabled there to avoid cross-loop reuse.
_engine_kwargs = {
    "echo": False,
    "connect_args": {
        "statement_cache_size": 0,  # Disables asyncpg prepared statement caching
        "prepared_statement_cache_size": 0,  # Extra safety for asyncpg variants
    },
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


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

