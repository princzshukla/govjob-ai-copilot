import os

# Must be set before app modules are imported: settings are read at import time.
os.environ.setdefault("GROQ_API_KEY", "test-key-not-used")
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/govjobs_test"
)
os.environ["COOKIE_SECURE"] = "false"

import httpx
import psycopg2
import pytest
import pytest_asyncio
from sqlalchemy import text

from app.core.database import AsyncSessionLocal, init_db
from app.core.rate_limit import limiter
from app.main import app

TEST_DB = "govjobs_test"


def _ensure_test_database() -> None:
    conn = psycopg2.connect(
        host="localhost", port=5432, user="postgres", password="postgres", dbname="postgres"
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB,))
            if cur.fetchone() is None:
                # Fixed identifier from this module, not user input.
                cur.execute(f'CREATE DATABASE "{TEST_DB}"')
    finally:
        conn.close()


_ensure_test_database()


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    # Every test hits login/register from the same test IP; reset the
    # 5-per-minute buckets so tests don't interfere with each other.
    limiter.reset()
    yield


@pytest_asyncio.fixture(autouse=True)
async def _prepare_db():
    await init_db()  # idempotent: creates tables on first use
    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM sessions"))
        await db.execute(text("DELETE FROM users"))
        await db.commit()
    yield


@pytest_asyncio.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
