from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models.exam import Base

# Model imports so metadata knows about all tables
import app.models.candidate  # noqa: F401
import app.models.exam       # noqa: F401
import app.models.roadmap    # noqa: F401
import app.models.syllabus   # noqa: F401
import app.models.adaptive   # noqa: F401
import app.models.auth       # noqa: F401

db_url = str(settings.DATABASE_URL)
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql+psycopg://"):
    db_url = db_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)

is_test = getattr(settings, "ENVIRONMENT", "") == "test"

engine_kwargs = {
    "echo": False,
    "connect_args": {
        "statement_cache_size": 0,           # Disables asyncpg prepared statement caching
        "prepared_statement_cache_size": 0,  # Extra safety for asyncpg variants
    },
}

if is_test:
    # Tests run each case in a fresh event loop; disable pooling to avoid cross-loop reuse
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(db_url, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session