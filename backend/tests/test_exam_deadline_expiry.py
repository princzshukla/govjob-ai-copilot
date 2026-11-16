"""Exam deadline auto-expiry.

Boundaries, using IST calendar dates (a deadline is open through end-of-day):

* deadline today            -> still open (IST)
* deadline yesterday        -> closed; hidden from the eligibility engine and
                               flipped inactive by the expiry job
* deadline in the future    -> open
* no deadline               -> never expired (shown as "check notification")
* extended deadline         -> a seed row whose deadline moved forward is
                               refreshed from the file and reopened even if the
                               expiry job had deactivated it
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.core import seed as seed_module
from app.core.seed import upsert_seed_exams
from app.core.tasks import expire_closed_exam_notifications
from app.core.timeutils import deadline_open, today_ist
from app.core.database import AsyncSessionLocal
from app.models.exam import ExamNotification


def test_deadline_open_boundary_today_and_yesterday():
    today = date(2026, 11, 15)
    assert deadline_open(today, today) is True
    assert deadline_open(today - timedelta(days=1), today) is False
    assert deadline_open(today + timedelta(days=1), today) is True
    assert deadline_open(None, today) is True  # missing deadline never expires


async def _get_exam(db, exam_id: str) -> ExamNotification | None:
    return (
        await db.execute(select(ExamNotification).where(ExamNotification.id == exam_id))
    ).scalar_one_or_none()


async def _make_exam(db, exam_id: str, deadline: date) -> ExamNotification:
    exam = ExamNotification(
        id=exam_id,
        title=f"Expiry boundary test {exam_id}",
        organizing_body="TEST",
        post_type="Test",
        application_deadline=deadline,
        min_age=18,
        max_age_general=35,
        age_cutoff_date=deadline,
        allowed_degrees=["Any Graduate"],
        allowed_streams=["Any"],
        min_percentage=0.0,
        is_active=True,
    )
    db.add(exam)
    await db.commit()
    return exam


async def test_expiry_job_hides_yesterday_but_keeps_today():
    today = today_ist()
    ids = [f"expiry-yesterday-{today.isoformat()}", f"expiry-today-{today.isoformat()}"]
    async with AsyncSessionLocal() as db:
        await _make_exam(db, ids[0], today - timedelta(days=1))
        await _make_exam(db, ids[1], today)

    expired = await expire_closed_exam_notifications()
    try:
        assert ids[0] in expired
        assert ids[1] not in expired
        async with AsyncSessionLocal() as db:
            assert (await _get_exam(db, ids[0])).is_active is False
            assert (await _get_exam(db, ids[1])).is_active is True
    finally:
        async with AsyncSessionLocal() as db:
            for eid in ids:
                row = await _get_exam(db, eid)
                if row is not None:
                    await db.delete(row)
            await db.commit()


async def test_extended_deadline_reopens_seed_row(monkeypatch):
    today = today_ist()
    seed_id = f"expiry-extend-{today.isoformat()}"
    original = dict(seed_module.SEED_EXAMS[0])
    original["id"] = seed_id
    # Deadline in the seed file is still in the past → row should not reopen.
    monkeypatch.setattr(
        seed_module,
        "SEED_EXAMS",
        [
            {**original, "application_deadline": today - timedelta(days=1)},
        ],
    )
    try:
        async with AsyncSessionLocal() as db:
            exam = await _make_exam(db, seed_id, today - timedelta(days=10))
            exam.is_active = False  # hidden by the expiry job
            await db.commit()

        # Not extended yet → the row must stay hidden.
        async with AsyncSessionLocal() as db:
            await upsert_seed_exams(db)
            row = await _get_exam(db, seed_id)
            assert row.is_active is False  # no extension yet → stays hidden

        monkeypatch.setattr(
            seed_module,
            "SEED_EXAMS",
            [
                {**original, "application_deadline": today + timedelta(days=30)},
            ],
        )
        async with AsyncSessionLocal() as db:
            await upsert_seed_exams(db)
            row = await _get_exam(db, seed_id)
            assert row.application_deadline == today + timedelta(days=30)
            assert row.is_active is True  # reopened after the extension
    finally:
        async with AsyncSessionLocal() as db:
            row = await _get_exam(db, seed_id)
            if row is not None:
                await db.delete(row)
            await db.commit()
