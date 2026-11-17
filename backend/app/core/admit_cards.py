"""Admit-card seed + idempotent upsert.

A small, hand-curated list of currently-live admit cards, sourced only from
official board notices/PDFs (links verified at seed time). Discovery-only
automation feeds this later; the eligibility pipeline never sees these rows.
"""
from __future__ import annotations

import logging
from datetime import date

logger = logging.getLogger(__name__)

# Verified against the official source on 2026-11-17 (both SSC PDFs returned
# HTTP 200 from ssc.gov.in; the UPSC page returned HTTP 200).
SEED_ADMIT_CARDS: list[dict] = [
    {
        "id": "ssc-si-dp-capf-2025-cpo-admit-card",
        "title": "SSC — Sub-Inspector in Delhi Police & CAPFs (2025), Paper-I: City of Examination & Admission Certificate",
        "organizing_body": "Staff Selection Commission (SSC)",
        "exam_name": "Sub-Inspector in Delhi Police and CAPFs Examination, 2025",
        "notification_date": date(2026, 11, 13),
        "exam_date": None,  # Paper-I date per the notice; not restated here on purpose
        "admit_url": "https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/City%20live%20CPO%20Exam%20notice_13112026.pdf",
        "source_url": "https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/City%20live%20CPO%20Exam%20notice_13112026.pdf",
        "last_checked_at": date(2026, 11, 17),
    },
    {
        "id": "ssc-cgept-01-02-2027-admit-card",
        "title": "SSC — Indian Coast Guard CGEPT 01/2027 & 02/2027: City of Examination & Admit Card",
        "organizing_body": "Staff Selection Commission (SSC)",
        "exam_name": "CGEPT 01/2027 & 02/2027 (Indian Coast Guard)",
        "notification_date": date(2026, 11, 6),
        "exam_date": None,
        "admit_url": "https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Englishnotice_06112026.pdf",
        "source_url": "https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Englishnotice_06112026.pdf",
        "last_checked_at": date(2026, 11, 17),
    },
    {
        "id": "upsc-ifs-main-2026-admit-card",
        "title": "UPSC — Indian Forest Service (Main) Examination 2026: e-Admit Card",
        "organizing_body": "Union Public Service Commission (UPSC)",
        "exam_name": "Indian Forest Service (Main) Examination, 2026",
        "notification_date": None,
        "exam_date": None,
        "admit_url": "https://www.upsc.gov.in/whats-new/Indian%20Forest%20Service%20%28Main%29%20Examination%2C%202026/e%20-%20Admit%20Card",
        "source_url": "https://www.upsc.gov.in/whats-new/Indian%20Forest%20Service%20%28Main%29%20Examination%2C%202026/e%20-%20Admit%20Card",
        "last_checked_at": date(2026, 11, 17),
    },
]

_REFRESHABLE_FIELDS = (
    "exam_name",
    "notification_date",
    "exam_date",
    "admit_url",
    "source_url",
    "last_checked_at",
)


async def upsert_admit_cards(db) -> int:
    """Insert missing seed admit cards; refresh provenance on existing rows.

    Reopens a row when a previously missing/moved-forward exam date arrives.
    Never overwrites admin deactivations unless the exam date actually moved
    forward. Returns the number of rows inserted.
    """
    from sqlalchemy import select

    from app.core.timeutils import today_ist
    from app.models.admit_card import AdmitCardNotification

    existing = {
        row.id: row
        for row in (await db.execute(select(AdmitCardNotification))).scalars().all()
    }
    inserted = 0
    refreshed = 0
    today = today_ist()
    for item in SEED_ADMIT_CARDS:
        row = existing.get(item["id"])
        if row is None:
            db.add(AdmitCardNotification(**item))
            inserted += 1
            continue
        changed = False
        new_exam = item.get("exam_date")
        if (
            new_exam is not None
            and row.exam_date is not None
            and new_exam > row.exam_date
            and not row.is_active
            and new_exam >= today
        ):
            row.is_active = True
            changed = True
        for field in _REFRESHABLE_FIELDS:
            value = item.get(field)
            if value != getattr(row, field):
                setattr(row, field, value)
                changed = True
        if changed:
            refreshed += 1
    if inserted or refreshed:
        await db.commit()
    if refreshed:
        logger.info("refreshed provenance for %d admit card rows", refreshed)
    return inserted
