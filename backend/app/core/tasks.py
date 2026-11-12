"""Background maintenance tasks.

The app runs a small in-process loop that prunes expired sessions once an
hour. It is safe to run from every worker: the DELETE is idempotent.
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import delete

from app.core.database import AsyncSessionLocal
from app.models.auth import Session

logger = logging.getLogger(__name__)


async def prune_expired_sessions() -> int:
    """Delete expired session rows; returns the number removed."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            delete(Session).where(Session.expires_at < datetime.now(timezone.utc))
        )
        await db.commit()
    return result.rowcount or 0


async def session_cleanup_loop(interval_seconds: int = 3600) -> None:
    while True:
        try:
            removed = await prune_expired_sessions()
            if removed:
                logger.info("Pruned %d expired sessions", removed)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Session cleanup failed")
        await asyncio.sleep(interval_seconds)
