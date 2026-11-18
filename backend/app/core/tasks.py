"""Background maintenance tasks.

The app runs a small in-process loop that prunes expired sessions once an
hour, and one that hides closed job notifications twice a day. Both are safe
to run from every worker: the writes are idempotent.
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import and_, delete, or_, select, update

from app.core.database import AsyncSessionLocal
from app.core.timeutils import today_ist
from app.models.admit_card import AdmitCardNotification
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


async def expire_stale_admit_cards() -> list[str]:
    """Hide admit cards whose exam is over (or older than 60 days).

    A card exists to be used around exam day: once ``exam_date`` passes it is
    noise. Cards without a published exam date age out 60 days after the
    notification was released. Hides, never deletes. Returns flipped ids.
    """
    from datetime import timedelta

    today = today_ist()
    cutoff = today - timedelta(days=60)
    async with AsyncSessionLocal() as db:
        due = list(
            (
                await db.execute(
                    select(AdmitCardNotification.id).where(
                        AdmitCardNotification.is_active.is_(True),
                        or_(
                            AdmitCardNotification.exam_date < today,
                            and_(
                                AdmitCardNotification.exam_date.is_(None),
                                AdmitCardNotification.notification_date.is_not(None),
                                AdmitCardNotification.notification_date < cutoff,
                            ),
                        ),
                    )
                )
            ).all()
        )
        flat_ids = [row[0] for row in due]
        if not flat_ids:
            return []
        await db.execute(
            update(AdmitCardNotification)
            .where(AdmitCardNotification.id.in_(flat_ids))
            .values(is_active=False)
        )
        await db.commit()
    logger.info("expired %d admit cards: %s", len(flat_ids), ", ".join(flat_ids))
    return flat_ids


async def check_admit_cards_links() -> list[str]:
    """Weekly liveness check on every active admit-card URL.

    Boards move/delete notice PDFs around and after exam day. This pass
    HEAD-requests each active admit_url (GET-range fallback for 405):

    * 2xx          → refresh last_checked_at (link is healthy)
    * 404 / 410    → flip is_active=False — the card is dead, hide it —
                     and Telegram the admin "admit card link died" finding
    * anything else (403/5xx/timeout/TLS) → leave unchanged; log + try next
                     week. A portal block never hides a live card.

    Returns the ids flipped inactive.
    """
    import httpx

    HEADERS = {"User-Agent": "govjob-copilot/0.1 (admit-card link health check)"}
    dead: list[str] = []
    refreshed = 0
    async with AsyncSessionLocal() as db:
        rows = list(
            (await db.execute(select(AdmitCardNotification).where(AdmitCardNotification.is_active.is_(True)))).scalars().all()
        )
        async with httpx.AsyncClient(timeout=15.0, headers=HEADERS, follow_redirects=True) as client:
            for row in rows:
                url = (row.admit_url or "").strip()
                if not url:
                    continue
                try:
                    resp = await client.head(url)
                    if resp.status_code == 405:
                        resp = await client.get(url, headers={**HEADERS, "Range": "bytes=0-0"})
                except Exception as exc:
                    logger.info("admit-card link check failed for %s (%s) — will retry weekly", url, type(exc).__name__)
                    continue
                if resp.status_code in (404, 410):
                    # Never deactivate candidate-portal rows on 4xx: boards
                    # routinely block non-browser clients (bot filtering) while
                    # the portal works fine in a real browser. Only files/pages
                    # are trustworthy enough to call "gone".
                    if (row.link_kind or "notice_pdf") in ("notice_pdf", "notice_page"):
                        row.is_active = False
                        dead.append(row.id)
                    else:
                        logger.info("portal row %s returned %s — treating as unverified, not dead", url, resp.status_code)
                elif resp.status_code < 400:
                    row.last_checked_at = today_ist()
                    refreshed += 1
                else:
                    logger.info("admit-card link %s returned %s — left visible, retry weekly", url, resp.status_code)
        if dead or refreshed:
            await db.commit()
    if dead:
        logger.warning("admit-card links unhealthy (%d): %s", len(dead), ", ".join(dead))
        try:
            from app.core.config import settings
            from app.services.notifier import send_telegram_alert

            if settings.TELEGRAM_ADMIN_CHAT_ID:
                await send_telegram_alert(
                    settings.TELEGRAM_ADMIN_CHAT_ID,
                    "Admit-card links went dead (%d): %s" % (len(dead), ", ".join(dead)),
                )
        except Exception:
            logger.exception("admit-card link-check alert failed — continuing")
    logger.info("admit-card link check done: %d refreshed, %d marked dead", refreshed, len(dead))
    return dead


async def admit_link_check_loop(interval_seconds: int = 7 * 24 * 3600) -> None:
    """Run the admit-card link liveness check once a week (and at startup)."""
    while True:
        try:
            await check_admit_cards_links()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Admit-card link check failed")
        await asyncio.sleep(interval_seconds)


async def exam_deadline_expiry_loop(interval_seconds: int = 12 * 3600) -> None:
    """Run the expiry pass twice a day (and once at startup)."""
    while True:
        try:
            expired = await expire_closed_exam_notifications()
            expired_cards = await expire_stale_admit_cards()
            if expired or expired_cards:
                try:
                    from app.services.notifier import send_telegram_alert
                    from app.core.config import settings

                    if settings.TELEGRAM_ADMIN_CHAT_ID:
                        parts = []
                        if expired:
                            parts.append(
                                f"Closed exam notifications hidden ({len(expired)}): "
                                + ", ".join(expired[:10])
                            )
                        if expired_cards:
                            parts.append(
                                f"Stale admit cards hidden ({len(expired_cards)}): "
                                + ", ".join(expired_cards[:10])
                            )
                        await send_telegram_alert(settings.TELEGRAM_ADMIN_CHAT_ID, "\n".join(parts))
                except Exception:
                    logger.exception("expiry admin alert failed — continuing")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            if "admit_cards" in str(e):
                logger.error(
                    "admit-card expiry skipped: table missing — "
                    "run `alembic upgrade head` (migration a1c3d5e7f901)"
                )
            else:
                logger.exception("Exam deadline expiry pass failed")
        await asyncio.sleep(interval_seconds)
