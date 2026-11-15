import os
import pathlib
from urllib.parse import unquote, urlparse

# Must be set before app modules are imported: settings are read at import time.
os.environ.setdefault("GROQ_API_KEY", "test-key-not-used")
os.environ["ENVIRONMENT"] = "test"
# CI or a developer can point tests at a disposable Postgres instance without
# editing this file. The default remains the local docker-compose database.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/govjobs_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["COOKIE_SECURE"] = "false"

import httpx
import psycopg2
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import text

from app.api.v1.endpoints import eligibility
from app.core.database import AsyncSessionLocal
from app.core.rate_limit import limiter
from app.main import app

_parsed_test_url = urlparse(TEST_DATABASE_URL)
TEST_DB = _parsed_test_url.path.lstrip("/") or "govjobs_test"
BACKEND_DIR = pathlib.Path(__file__).resolve().parents[1]


def _recreate_test_database() -> None:
    """Drop and recreate the test database so every run starts from migrations.

    Only the fixed TEST_DB identifier from this module is used; no user input
    reaches the SQL. WITH (FORCE) (Postgres 13+) drops stale connections from
    an interrupted run.
    """
    conn = psycopg2.connect(
        host=_parsed_test_url.hostname or "localhost",
        port=_parsed_test_url.port or 5432,
        user=unquote(_parsed_test_url.username or "postgres"),
        password=unquote(_parsed_test_url.password or ""),
        dbname="postgres",
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)')
            cur.execute(f'CREATE DATABASE "{TEST_DB}"')
    finally:
        conn.close()


def _run_migrations() -> None:
    """Build the test schema with the real Alembic migrations.

    Using migrations instead of ``Base.metadata.create_all`` means a broken or
    drifted migration fails the test suite, not production.
    """
    config = AlembicConfig(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(config, "head")


@pytest.fixture(scope="session", autouse=True)
def _migrated_database():
    _recreate_test_database()
    _run_migrations()
    yield


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    # Every test hits login/register from the same test IP; reset the
    # 5-per-minute buckets so tests don't interfere with each other.
    limiter.reset()
    # The live-job sync cooldown is process-wide by design; reset it per test.
    eligibility._last_sync_started_at = None
    yield


@pytest_asyncio.fixture(autouse=True)
async def _prepare_db():
    async with AsyncSessionLocal() as db:
        # One atomic reset of everything user-reachable, instead of three
        # separate DELETEs (which aborted mid-way under lock pressure and
        # left partially-deleted state between tests).
        await db.execute(
            text("TRUNCATE question_bank, sessions, users RESTART IDENTITY CASCADE")
        )
        await db.commit()
    yield


@pytest_asyncio.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
