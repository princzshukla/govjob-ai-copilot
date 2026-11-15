"""Startup seed hook: idempotent upsert of SEED_EXAMS.

Whatever the current state of exam_notifications, the hook inserts only the
missing rows; existing rows (edited/retired by admins) are preserved.
"""
from datetime import date

import pytest
from sqlalchemy import delete, func, select

from app.core.database import AsyncSessionLocal
from app.core.seed import SEED_EXAMS, upsert_seed_exams
from app.models.exam import ExamNotification


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


async def test_upsert_inserts_missing_rows_only(db):
    target = SEED_EXAMS[0]["id"]
    await db.execute(delete(ExamNotification).where(ExamNotification.id == target))
    await db.commit()

    first = await upsert_seed_exams(db)
    assert first >= 1

    count = (
        await db.execute(select(func.count()).select_from(ExamNotification).where(ExamNotification.id == target))
    ).scalar_one()
    assert count == 1

    second = await upsert_seed_exams(db)
    assert second == 0


async def test_upsert_never_overwrites_existing_rows(db):
    victim = SEED_EXAMS[1]
    exam = (
        await db.execute(select(ExamNotification).where(ExamNotification.id == victim["id"]))
    ).scalar_one_or_none()
    if exam is None:
        await upsert_seed_exams(db)
        exam = (
            await db.execute(select(ExamNotification).where(ExamNotification.id == victim["id"]))
        ).scalar_one()
    exam.organizing_body = "EDITED BY ADMIN"
    await db.commit()

    inserted = await upsert_seed_exams(db)
    assert inserted == 0  # nothing missing → nothing inserted

    await db.refresh(exam)
    assert exam.organizing_body == "EDITED BY ADMIN"
