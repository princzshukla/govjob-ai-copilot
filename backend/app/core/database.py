from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models.exam import Base

# Tests run each case in a fresh event loop and asyncpg connections are
# loop-bound, so pooling is disabled there to avoid cross-loop reuse.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    poolclass=NullPool if settings.ENVIRONMENT == "test" else None,
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    # Import models so their tables are registered on Base.metadata first.
    from app.models import auth  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
