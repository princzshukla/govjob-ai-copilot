# app/api/v1/endpoints/admin.py
"""Operator review queue for held extractions.

Gated by ``require_admin`` (ADMIN_EMAILS allowlist). Held rows
(``extraction_results.status == 'review'``) are shown with their evidence
quotes and the PDF link; an operator can approve (promote via the publish
gate), reject (never publish), or edit specific fields (the publish gate
validates them again).
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_admin
from app.core.database import get_db
from app.models.exam import ExamNotification
from app.models.pipeline import ExtractionResult, RawDiscoveredLink, ScrapeSource
from app.services.exam_publisher import publish_auto_extractions

router = APIRouter(prefix="/admin", tags=["Admin"])


class ReviewQueueItem(BaseModel):
    id: int
    source_slug: str
    source_name: str
    organizing_body: str
    url: str
    title: Optional[str]
    created_at: object
    missing_fields: list
    review_note: Optional[str]
    extracted: dict
    evidence: dict
    field_confidence: dict
    exam_notification_id: Optional[str]


@router.get("/review-queue", response_model=list[ReviewQueueItem])
async def list_review_queue(db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    rows = (
        await db.execute(
            select(ExtractionResult, RawDiscoveredLink, ScrapeSource)
            .join(RawDiscoveredLink, ExtractionResult.raw_link_id == RawDiscoveredLink.id)
            .join(ScrapeSource, RawDiscoveredLink.source_id == ScrapeSource.id)
            .where(ExtractionResult.status == "review")
            .order_by(ExtractionResult.created_at.desc())
            .limit(100)
        )
    ).all()
    items = []
    for extraction, link, source in rows:
        items.append(
            ReviewQueueItem(
                id=extraction.id,
                source_slug=source.slug,
                source_name=source.name,
                organizing_body=str((source.config or {}).get("organizing_body") or source.name),
                url=link.url,
                title=link.title,
                created_at=extraction.created_at,
                missing_fields=extraction.missing_fields or [],
                review_note=extraction.review_note,
                extracted=extraction.extracted or {},
                evidence=extraction.evidence or {},
                field_confidence=extraction.field_confidence or {},
                exam_notification_id=extraction.exam_notification_id,
            )
        )
    return items


async def _promote(row_id: int, db: AsyncSession) -> ExamNotification:
    row = (
        await db.execute(select(ExtractionResult).where(ExtractionResult.id == row_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction not found")
    row.status = "auto"
    await db.commit()
    report = await publish_auto_extractions(db)
    promoted = next((p for p in report.published if p.extraction_id == row.id), None)
    if promoted is None:
        held = next((h for h in report.held if h.extraction_id == row.id), None)
        reason = held.detail if held else "publish gate held the row"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot publish: {reason}",
        )
    exam = (
        await db.execute(select(ExamNotification).where(ExamNotification.id == promoted.exam_id))
    ).scalar_one()
    return exam


@router.post("/review-queue/{result_id}/approve")
async def approve(result_id: int, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    """Mark the row trusted and promote it through the publish gate.

    If the gate cannot publish (missing/unparseable required field), the row
    stays in review and the reasons are returned.
    """
    exam = await _promote(result_id, db)
    return {"status": "promoted", "exam_id": exam.id, "title": exam.title}


@router.post("/review-queue/{result_id}/reject")
async def reject(result_id: int, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    row = (
        await db.execute(select(ExtractionResult).where(ExtractionResult.id == result_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction not found")
    row.status = "rejected"
    await db.commit()
    return {"status": "rejected"}


class AdminEdit(BaseModel):
    total_vacancies: Optional[int] = None
    min_age: Optional[int] = None
    age_max_general: Optional[int] = None
    age_cutoff_date: Optional[str] = None
    required_qualification: Optional[str] = None
    application_last_date: Optional[str] = None
    pay_level: Optional[str] = None
    age_relaxations: Optional[dict] = None


@router.post("/review-queue/{result_id}/edit")
async def edit(
    result_id: int,
    payload: AdminEdit,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    """Patch specific fields, then promote through the gate (which re-validates).

    The admin owns the correctness of what they typed; the publish gate still
    enforces completeness/plausibility before publishing to users.
    """
    row = (
        await db.execute(select(ExtractionResult).where(ExtractionResult.id == result_id))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction not found")

    merged = dict(row.extracted or {})
    provided = payload.model_dump(exclude_unset=True)
    for key, value in provided.items():
        merged[key] = value
    if payload.age_relaxations is not None:
        merged["age_relaxations"] = payload.age_relaxations
    row.extracted = merged
    row.review_note = ((row.review_note or "").strip() + " | edited by admin").strip(" |") or None
    await db.commit()
    exam = await _promote(result_id, db)
    return {"status": "promoted", "exam_id": exam.id, "title": exam.title}
