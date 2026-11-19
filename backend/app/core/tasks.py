"""Background maintenance tasks.

The app runs a small in-process loop that prunes expired sessions once an
hour, and one that hides closed job notifications twice a day. Both are safe
to run from every worker: the writes are idempotent.
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import and_, delete, or_, select, update

from app.core.config import settings
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


LINK_FAILURE_DEACTIVATE_THRESHOLD = 2


async def probe_admit_link(client, url: str, headers: dict[str, str]) -> dict:
    """Probe one admit-card URL conservatively.

    HEAD is tried first. A 404/410/405 response is *inconclusive* — many
    boards reject HEAD but serve GET — so a ranged GET follows. Only a
    confirmed GET 404/410 can lead (eventually) to deactivation. 403/429,
    5xx and network errors are always inconclusive.
    """
    attempts = 0
    method = "HEAD"
    status = 0
    try:
        response = await client.head(url)
        attempts = 1
        method, status = "HEAD", response.status_code
        if status in (404, 410, 405):
            response = await client.get(url, headers={**headers, "Range": "bytes=0-0"})
            attempts = 2
            method, status = "GET", response.status_code
    except Exception as exc:
        return {
            "method": method,
            "status": status,
            "attempts": max(1, attempts),
            "reachable": False,
            "confirmed_dead": False,
            "decision": f"inconclusive: {type(exc).__name__}",
        }

    if 200 <= status < 300:
        verdict = "reachable"
    elif method == "GET" and status in (404, 410):
        verdict = "confirmed_dead"
    elif status in (403, 429) or status >= 500:
        verdict = "inconclusive: throttled/server error"
    else:
        verdict = "inconclusive: unverified response"
    return {
        "method": method,
        "status": status,
        "attempts": attempts,
        "reachable": verdict == "reachable",
        "confirmed_dead": verdict == "confirmed_dead",
        "decision": verdict,
    }


def link_health_decision(row, probe: dict, threshold: int = LINK_FAILURE_DEACTIVATE_THRESHOLD) -> tuple[int, bool, str]:
    """Return ``(new_fail_count, deactivate, decision_note)`` for one row."""
    if probe["reachable"]:
        return 0, False, f"reachable via {probe['method']} {probe['status']}; counter reset"
    if not probe["confirmed_dead"]:
        return (
            row.link_fail_count or 0,
            False,
            f"inconclusive ({probe['method']} {probe['status']}): {probe['decision']}; kept visible",
        )
    count = (row.link_fail_count or 0) + 1
    if (row.link_kind or "notice_pdf") == "candidate_portal":
        return count, False, f"portal returned 404/410 x{count}; candidate portals are never deactivated"
    if count >= threshold:
        return count, True, f"confirmed 404/410 x{count} via {probe['method']}; deactivated"
    return count, False, f"confirmed 404/410 x{count}/{threshold}; kept visible"


async def check_admit_cards_links(
    link_failure_threshold: int = LINK_FAILURE_DEACTIVATE_THRESHOLD,
) -> list[str]:
    """Weekly liveness sweep of active admit-card URLs.

    A link is hidden only after ``link_failure_threshold`` consecutive
    sweeps return a *confirmed* GET 404/410. HEAD 404, 405, 403/429, 5xx
    and timeouts are inconclusive and leave the card visible. Every decision
    is logged with the HTTP method, status, retry count and outcome.
    """
    import httpx

    headers = {"User-Agent": "govjob-copilot/0.1 (admit-card link health check)"}
    dead: list[str] = []
    refreshed = 0
    changed = False
    async with AsyncSessionLocal() as db:
        rows = list(
            (await db.execute(select(AdmitCardNotification).where(AdmitCardNotification.is_active.is_(True)))).scalars().all()
        )
        async with httpx.AsyncClient(timeout=15.0, headers=headers, follow_redirects=True) as client:
            for row in rows:
                url = (row.admit_url or "").strip()
                if not url:
                    continue
                probe = await probe_admit_link(client, url, headers)
                fail_count, deactivate, note = link_health_decision(row, probe, link_failure_threshold)
                logger.info(
                    "admit-card link %s (%s): %s %s, attempt %d/%d, decision: %s",
                    row.id, url, probe["method"], probe["status"],
                    probe["attempts"], link_failure_threshold, note,
                )
                row.link_fail_count = fail_count
                # A confirmed-dead first strike increments the counter but does
                # not deactivate yet. Commit it, otherwise the rollback at the
                # end of the sweep resets the counter and the two-strike rule
                # can never fire.
                changed = True
                # Preserve prior operator context (e.g. why a row was restored)
                # alongside the latest sweep decision.
                previous_note = (row.link_health_note or "").strip()
                merged_note = f"{previous_note} | {note}" if previous_note else note
                row.link_health_note = merged_note[-1000:]
                if deactivate:
                    row.is_active = False
                    dead.append(row.id)
                elif probe["reachable"]:
                    row.last_checked_at = today_ist()
                    refreshed += 1
        if changed:
            await db.commit()
    if dead:
        logger.warning("admit-card links unhealthy (%d): %s", len(dead), ", ".join(dead))
        try:
            from app.services.notifier import send_admin_alert

            if settings.TELEGRAM_ADMIN_CHAT_ID:
                await send_admin_alert(
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
                    from app.services.notifier import send_admin_alert

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
                        await send_admin_alert("\n".join(parts))
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
