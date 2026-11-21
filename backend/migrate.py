"""Apply Alembic migrations under a PostgreSQL advisory lock.

Container start runs this before uvicorn. Without the lock, two instances in a
rolling deploy both execute DDL and the loser crashes with a duplicate-column
error. A session-level advisory lock serialises them; it is released when this
process exits (even on failure).
"""

import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import psycopg2
from alembic import command
from alembic.config import Config

# Arbitrary but stable 64-bit key shared by every instance of this service.
_LOCK_KEY = 8612345678901234567


def main() -> None:
    url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    # libpq understands sslmode but not channel_binding on older clients.
    parts = urlsplit(url)
    params = dict(parse_qsl(parts.query))
    params.pop("channel_binding", None)
    url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(params), parts.fragment))
    conn = psycopg2.connect(url, connect_timeout=30)
    try:
        with conn.cursor() as cur:
            cur.execute("SET lock_timeout = '60s'")
            cur.execute("SELECT pg_advisory_lock(%s)", (_LOCK_KEY,))
        try:
            config = Config("alembic.ini")
            command.upgrade(config, "head")
        finally:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(%s)", (_LOCK_KEY,))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
