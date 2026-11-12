# app/services/roadmap_store.py
"""Atomic, idempotent helpers for saved roadmaps and week progress.

All persistence for the ``/me`` endpoints goes through PostgreSQL upserts so a
repeated request produces the same state instead of a duplicate row or a 500.
"""
import uuid
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.roadmap import SavedRoadmap
from app.models.progress import RoadmapProgress
from app.schemas.roadmap import StudyRoadmapResponse


async def upsert_saved_roadmap(
    db: AsyncSession,
    *,
    user_id: int,
    exam_id: str,
    target_weeks: int,
    roadmap: StudyRoadmapResponse,
) -> str:
    """Insert or replace a user's saved roadmap for an exam; return its id.

    ON CONFLICT keeps the existing row (and therefore its roadmap id and any
    week-progress rows attached to it) instead of deleting/recreating it.
    """
    values = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "exam_id": exam_id,
        "target_weeks": target_weeks,
        "roadmap_json": roadmap.model_dump(mode="json"),
    }
    stmt = pg_insert(SavedRoadmap).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "exam_id"],
        set_={
            "target_weeks": target_weeks,
            "roadmap_json": roadmap.model_dump(mode="json"),
        },
    ).returning(SavedRoadmap.id)
    row_id = (await db.execute(stmt)).scalar_one()
    await db.commit()
    return row_id


async def get_completed_weeks(db: AsyncSession, roadmap_id: str) -> list[int]:
    rows = (
        await db.execute(
            select(RoadmapProgress.week_no)
            .where(RoadmapProgress.roadmap_id == roadmap_id)
            .order_by(RoadmapProgress.week_no)
        )
    ).scalars().all()
    return list(rows)


def progress_payload(
    roadmap_id: str,
    target_weeks: int,
    completed_weeks: Iterable[int],
) -> dict:
    weeks = sorted(set(completed_weeks))
    count = len(weeks)
    percent = int(round(100 * count / target_weeks)) if target_weeks > 0 else 0
    return {
        "roadmap_id": roadmap_id,
        "target_weeks": target_weeks,
        "completed_weeks": weeks,
        "completed_count": count,
        "percent": percent,
    }
