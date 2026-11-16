"""Background maintenance tasks.

The app runs a small in-process loop that prunes expired sessions once an
hour, and one that hides closed job notifications twice a day. Both are safe
to run from every worker: the writes are idempotent.
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select, update

from app.core.database import AsyncSessionLocal
from app.core.timeutils import today_ist
from app.models.auth import Session
from app.models.exam import ExamNotification

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


async def expire_closed_exam_notifications() -> list[str]:
    """Hide job notifications whose deadline has passed (IST, end-of-day).

    Hides, never deletes: rows keep full history and can be reopened when a
    deadline is extended (see the seed refresh in app/core/seed.py and the
    Layer-2 publish path, which inserts new rows for new notifications).
    Rows with no deadline are never expired. Returns the ids of the rows that
    were flipped inactive.
    """
    async with AsyncSessionLocal() as db:
        due = list(
            (
                await db.execute(
                    select(ExamNotification.id, ExamNotification.title).where(
                        ExamNotification.is_active.is_(True),
                        ExamNotification.application_deadline.is_not(None),
                        ExamNotification.application_deadline < today_ist(),
                    )
                )
            ).all()
        )
        if not due:
            return []
        await db.execute(
            update(ExamNotification)
            .where(ExamNotification.id.in_([row.id for row in due]))
            .values(is_active=False)
        )
        await db.commit()
    logger.info(
        "expired %d exam notifications: %s",
        len(due),
        ", ".join(row.id for row in due),
    )
    return [row.id for row in due]


async def exam_deadline_expiry_loop(interval_seconds: int = 12 * 3600) -> None:
    """Run the expiry pass twice a day (and once at startup)."""
    while True:
        try:
            expired = await expire_closed_exam_notifications()
            if expired:
                try:
                    from app.services.notifier import send_telegram_alert
                    from app.core.config import settings

                    if settings.TELEGRAM_ADMIN_CHAT_ID:
                        await send_telegram_alert(
                            settings.TELEGRAM_ADMIN_CHAT_ID,
                            f"📅 Closed exam notifications hidden ({len(expired)}): "
                            + ", ".join(expired[:10]),
                        )
                except Exception:
                    logger.exception("expiry admin alert failed — continuing")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Exam deadline expiry pass failed")
        await asyncio.sleep(interval_seconds)
