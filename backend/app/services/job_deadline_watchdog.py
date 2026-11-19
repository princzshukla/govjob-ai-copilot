"""Deadline watchdog for job notifications.

Re-reads the *official* notice for active exams and detects extended or
revised closing dates, changed opening dates, and cancellations. Every change
is written to an append-only audit table with the previous value preserved.
No aggregator content is ever used as evidence, and no unverified value is
written to an exam notification.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

import httpx
from sqlalchemy import or_, select

from app.core.timeutils import today_ist
from app.models.exam import ExamNotification
from app.models.exam_changes import ExamNotificationChange
from app.services import jobs_watchdog as jw
from app.services import notification_extractor as nx

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 25
_HEADERS = {"User-Agent": "govjob-copilot/0.1 (official deadline verification)"}
_MAX_PDF_BYTES = 25 * 1024 * 1024


def _as_text(value):
    """Audit columns are TEXT; normalize bools/dates before binding."""
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _record_change(db, exam: ExamNotification, *, field: str, old, new,
                   kind: str, source: str | None, note: str | None) -> None:
    db.add(ExamNotificationChange(
        exam_id=exam.id, field=field, old_value=_as_text(old),
        new_value=_as_text(new), change_kind=kind, source_url=source,
        note=(note or "")[:1000] or None,
    ))


async def _fetch_notice_text(url: str, client: httpx.AsyncClient) -> tuple[str, bool]:
    """Return (text, is_official_pdf). Failures raise to the caller."""
    response = await client.get(url, timeout=25)
    if response.status_code in (404, 410):
        return "", False
    response.raise_for_status()
    body = response.content
    if body.startswith(b"%PDF-"):
        if len(body) > _MAX_PDF_BYTES:
            raise ValueError("pdf_too_large")
        text, _pages, _cpp = nx.extract_text_stats(body)
        return text, True
    return body.decode(response.encoding or "utf-8", errors="ignore"), False


async def check_exam_deadlines(
    db,
    *,
    limit: int = DEFAULT_LIMIT,
    today: date | None = None,
    client: httpx.AsyncClient | None = None,
    min_overlap: float = 0.25,
) -> dict:
    """Check a bounded slice of active exams against their official notice."""
    today = today or today_ist()
    stats = {"checked": 0, "updated": 0, "cancelled": 0, "unchanged": 0,
             "failed": 0, "audit_rows": 0, "skipped": 0}
    stmt = (
        select(ExamNotification)
        .where(
            ExamNotification.is_active.is_(True),
            or_(
                ExamNotification.application_deadline.is_(None),
                ExamNotification.application_deadline >= today - timedelta(days=30),
            ),
            or_(
                ExamNotification.source_url.like("http%"),
                ExamNotification.official_pdf_url.like("http%"),
            ),
            # Only due rows consume the daily request budget; otherwise the
            # seeded backlog would crowd out a genuinely changed notice.
            or_(
                ExamNotification.last_checked_at.is_(None),
                ExamNotification.last_checked_at < today,
            ),
        )
        .order_by(ExamNotification.application_deadline.asc().nulls_last())
        .limit(limit)
    )
    exams = list((await db.execute(stmt)).scalars().all())

    async def _run(client_: httpx.AsyncClient) -> None:
        from app.services import discovery_engine as de

        for exam in exams:
            exam_id = exam.id
            url = exam.source_url or exam.official_pdf_url
            if exam.last_checked_at == today:
                stats["skipped"] += 1  # already checked today — be a good citizen
                continue
            stats["checked"] += 1
            try:
                text, is_pdf = await _fetch_notice_text(url, client_)
                if not text:  # 404/410 on the official URL
                    exam.is_active = False
                    exam.last_checked_at = today
                    _record_change(db, exam, field="is_active", old=True, new=False,
                                   kind="notice_unavailable", source=url,
                                   note="official notice URL returned 404/410")
                    stats["cancelled"] += 1
                    stats["audit_rows"] += 1
                    await db.commit()
                    continue
                # Official-domain evidence only: the title must appear in the
                # fetched document. No third-party page can pass this check.
                if de._token_overlap(exam.title, text) < min_overlap:
                    stats["failed"] += 1
                    logger.info("deadline check skipped for %s — title not in official notice", exam.id)
                    await db.rollback()
                    continue

                fields = jw.extract_job_fields(text)
                changed = False
                if fields["cancelled"]:
                    exam.is_active = False
                    _record_change(db, exam, field="is_active", old=True, new=False,
                                   kind="cancelled", source=url,
                                   note="cancellation/withdrawal stated in official notice")
                    stats["cancelled"] += 1
                    stats["audit_rows"] += 1
                    changed = True
                else:
                    closing = fields.get("application_last_date")
                    if closing:
                        closing_date = date.fromisoformat(closing)
                        if closing_date != exam.application_deadline:
                            kind = ("deadline_extended" if closing_date > exam.application_deadline
                                    else "deadline_revised")
                            _record_change(db, exam, field="application_deadline",
                                           old=exam.application_deadline, new=closing_date,
                                           kind=kind, source=url,
                                           note="official notice re-read by jobs watchdog")
                            exam.application_deadline = closing_date
                            if not exam.is_active and closing_date >= today:
                                exam.is_active = True
                            stats["updated"] += 1
                            stats["audit_rows"] += 1
                            changed = True
                    opening = fields.get("application_start_date")
                    if opening:
                        opening_date = date.fromisoformat(opening)
                        if opening_date != exam.application_start_date:
                            _record_change(db, exam, field="application_start_date",
                                           old=exam.application_start_date, new=opening_date,
                                           kind="opening_date_changed", source=url,
                                           note="official notice re-read by jobs watchdog")
                            exam.application_start_date = opening_date
                            stats["updated"] += 1
                            stats["audit_rows"] += 1
                            changed = True
                    if fields.get("revised") and not changed:
                        _record_change(db, exam, field="notice", old=None, new="revised",
                                       kind="notice_revised", source=url,
                                       note="corrigendum/addendum wording in official notice")
                        stats["audit_rows"] += 1
                        changed = True

                exam.verified_on = today
                exam.verification_status = "verified"
                exam.last_checked_at = today
                exam.deadline_locked = True  # startup seed refresh must not undo this
                if not changed:
                    stats["unchanged"] += 1
                await db.commit()
            except Exception:
                stats["failed"] += 1
                logger.exception("deadline check failed for exam %s (%s)", exam_id, url)
                await db.rollback()

    if client is None:
        async with httpx.AsyncClient(headers=_HEADERS, follow_redirects=True) as owned:
            await _run(owned)
    else:
        await _run(client)
    logger.info("deadline watchdog run: %s", stats)
    return stats
