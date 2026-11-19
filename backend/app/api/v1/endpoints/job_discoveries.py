# app/api/v1/endpoints/job_discoveries.py
"""Admin review for job discoveries found by the Jobs Coverage Watchdog.

Research queue only. A record can be approved only with verified official
evidence, and approval writes through the existing SEED_EXAMS overlay +
upsert_seed_exams() path — never a second publishing pipeline.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_admin
from app.core.database import get_db
from app.core.seed import record_approved_job_seed, upsert_seed_exams
from app.core.timeutils import today_ist
from app.models.discovery import DiscoveryHistory, NotificationDiscovery
from app.services import discovery_engine as de
from app.services import jobs_watchdog as jw
from app.services.matcher import degrees_and_streams_from_text

router = APIRouter(prefix="/admin/job-discoveries", tags=["Admin: Job Discovery"])


class DuplicateRequest(BaseModel):
    duplicate_reference: str


class ApproveJobDiscovery(BaseModel):
    """Operator-supplied values for fields the official PDF did not state.

    Nothing here is guessed by the system: it is the human review step. All
    fields are optional; missing critical values keep the record in review.
    """

    title: str | None = None
    organizing_body: str | None = None
    official_pdf_url: str | None = None
    apply_url: str | None = None
    application_deadline: date | None = None
    application_start_date: date | None = None
    age_cutoff_date: date | None = None
    min_age: int | None = Field(default=None, ge=10, le=65)
    max_age_general: int | None = Field(default=None, ge=15, le=75)
    required_qualification: str | None = None
    allowed_degrees: list[str] | None = None
    notification_date: date | None = None
    post_type: str = "General"
    note: str = Field(default="", max_length=1000)


def _item(record: NotificationDiscovery) -> dict:
    info = record.extracted_information or {}
    return {
        "id": record.id,
        "notification_kind": record.notification_kind,
        "classification": record.classification,
        "aggregator_title": record.aggregator_title,
        "aggregator_url": record.aggregator_url,
        "organization": record.organization,
        "recruitment_year": record.recruitment_year,
        "official_website": record.official_website,
        "official_notification_url": record.official_notification_url,
        "official_pdf_url": record.official_pdf_url,
        "verification_status": record.verification_status,
        "discovery_status": record.discovery_status,
        "confidence_score": record.confidence_score,
        "duplicate_reference": record.duplicate_reference,
        "fields": info.get("fields") or {},
        "verification": info.get("verification") or {},
        "analysis": info.get("analysis") or {},
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


async def _get(db: AsyncSession, record_id: int) -> NotificationDiscovery:
    record = (
        await db.execute(
            select(NotificationDiscovery).where(
                NotificationDiscovery.id == record_id,
                NotificationDiscovery.notification_kind == "job",
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job discovery not found")
    return record


@router.get("")
async def list_job_discoveries(
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
    discovery_status: str | None = Query(default=None),
    classification: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    stmt = select(NotificationDiscovery).where(NotificationDiscovery.notification_kind == "job")
    if discovery_status:
        stmt = stmt.where(NotificationDiscovery.discovery_status == discovery_status)
    if classification:
        stmt = stmt.where(NotificationDiscovery.classification == classification)
    rows = (await db.execute(stmt.order_by(NotificationDiscovery.id.desc()).limit(limit))).scalars().all()
    return {"total": len(rows), "discoveries": [_item(r) for r in rows]}


@router.get("/{record_id}")
async def get_job_discovery(record_id: int, db: AsyncSession = Depends(get_db),
                            admin=Depends(require_admin)):
    return _item(await _get(db, record_id))


@router.get("/{record_id}/history")
async def job_discovery_history(record_id: int, db: AsyncSession = Depends(get_db),
                                admin=Depends(require_admin)):
    await _get(db, record_id)
    rows = (await db.execute(
        select(DiscoveryHistory)
        .where(DiscoveryHistory.discovery_id == record_id)
        .order_by(DiscoveryHistory.id)
    )).scalars().all()
    return [{
        "id": row.id, "from_status": row.from_status, "to_status": row.to_status,
        "actor": row.actor, "note": row.note, "created_at": row.created_at,
    } for row in rows]


@router.post("/scan")
async def scan_unmatched_jobs(db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    """Run the jobs watchdog coverage pass and queue current gaps for review."""
    report = await jw.check_jobs_coverage_async()
    stats = await jw.run_jobs_discovery(db, report)
    return {"unmatched": len(report.missing), **stats}


@router.post("/{record_id}/approve")
async def approve_job_discovery(
    record_id: int,
    payload: ApproveJobDiscovery,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    """Promote an officially verified discovery into SEED_EXAMS.

    The publish gate is deliberately strict: an official URL, official
    evidence and all values required by exam_notifications must be present.
    A missing value leaves the record in review with a machine-readable note.
    """
    record = await _get(db, record_id)
    info = record.extracted_information or {}
    fields = info.get("fields") or {}
    reason = de.validate_approval(record)
    if reason:
        code = (status.HTTP_409_CONFLICT if reason.startswith("invalid status")
                else status.HTTP_422_UNPROCESSABLE_ENTITY)
        raise HTTPException(status_code=code, detail=f"Approval refused: {reason}")

    official_url = record.official_pdf_url or record.official_notification_url
    values = {
        "application_deadline": payload.application_deadline or fields.get("application_last_date"),
        "application_start_date": payload.application_start_date or fields.get("application_start_date"),
        "age_cutoff_date": payload.age_cutoff_date,
        "min_age": payload.min_age if payload.min_age is not None else fields.get("min_age"),
        "max_age_general": (payload.max_age_general if payload.max_age_general is not None
                            else fields.get("age_max_general")),
        "required_qualification": payload.required_qualification or fields.get("required_qualification"),
    }
    missing = [key for key in ("application_deadline", "min_age", "max_age_general",
                               "age_cutoff_date", "required_qualification")
               if values[key] is None]
    if missing:
        # Stay in review — never invent a value to reach a confident verdict.
        previous = record.discovery_status
        note = f"Approval held: missing required fields {', '.join(missing)}" + (
            f" | {payload.note}" if payload.note else ""
        )
        await de.add_history(db, record, previous, record.discovery_status, note, actor=admin.email)
        await db.commit()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"reason": "missing_required_fields", "fields": missing})

    # Dates extracted from the PDF arrive as ISO strings.
    for key in ("application_deadline", "application_start_date"):
        if isinstance(values[key], str):
            values[key] = date.fromisoformat(values[key])

    if payload.allowed_degrees:
        degrees = payload.allowed_degrees
    else:
        degrees, _streams = degrees_and_streams_from_text(str(values["required_qualification"]))
    if not degrees:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={"reason": "unmappable_qualification"})

    analysis = info.get("analysis") or {}
    official_url = (payload.official_pdf_url or record.official_pdf_url
                    or record.official_notification_url)
    existing = await de.collect_existing(db, exclude_id=record.id, notification_kind="job")
    duplicate = de.detect_duplicate(analysis=analysis, official_url=official_url, existing=existing)
    if duplicate["is_duplicate"]:
        record.discovery_status = de.STATUS_DUPLICATE
        record.duplicate_reference = duplicate["reference"]
        record.verification_status = "duplicate"
        await de.add_history(db, record, record.discovery_status, de.STATUS_DUPLICATE,
                             f"Approval re-check: {duplicate['reason']}", actor=admin.email)
        await db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Duplicate of {duplicate['reference']} ({duplicate['reason']})")

    seed_id = f"disc-{record.id}"[:36]
    seed_item = {
        "id": seed_id,
        "title": (payload.title or record.aggregator_title)[:255],
        "organizing_body": (payload.organizing_body or record.organization or "Unknown").upper()[:100],
        "post_type": payload.post_type[:50],
        "notification_date": payload.notification_date,
        "application_deadline": values["application_deadline"],
        "application_start_date": values["application_start_date"],
        "exam_date": None,
        "official_pdf_url": official_url,
        "source_url": official_url,
        "apply_url": payload.apply_url,
        "verified_on": today_ist(),
        "verification_status": "verified",
        "min_age": int(values["min_age"]),
        "max_age_general": int(values["max_age_general"]),
        "age_cutoff_date": values["age_cutoff_date"],
        "allowed_degrees": degrees,
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": set(),
        "last_checked_at": today_ist(),
    }
    try:
        record_approved_job_seed(seed_item)
        await upsert_seed_exams(db)  # existing architecture, no second pipeline
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    previous = record.discovery_status
    record.discovery_status = de.STATUS_APPROVED
    await de.add_history(
        db, record, previous, de.STATUS_APPROVED,
        f"Approved by {admin.email}; seed {seed_id}; official evidence {official_url[:120]}"
        + (f" | {payload.note}" if payload.note else ""),
        actor=admin.email,
    )
    await db.commit()
    await db.refresh(record)
    return {"status": "approved", "seed_id": seed_id, "record": _item(record)}


@router.post("/{record_id}/reject")
async def reject_job_discovery(record_id: int, db: AsyncSession = Depends(get_db),
                               admin=Depends(require_admin)):
    record = await _get(db, record_id)
    previous = record.discovery_status
    record.discovery_status = de.STATUS_REJECTED
    await de.add_history(db, record, previous, de.STATUS_REJECTED,
                         "Rejected by admin", actor=admin.email)
    await db.commit()
    return {"status": "rejected", "id": record.id}


@router.post("/{record_id}/mark-duplicate")
async def mark_job_duplicate(record_id: int, payload: DuplicateRequest,
                             db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    record = await _get(db, record_id)
    previous = record.discovery_status
    record.discovery_status = de.STATUS_DUPLICATE
    record.duplicate_reference = payload.duplicate_reference
    await de.add_history(db, record, previous, de.STATUS_DUPLICATE,
                         f"Marked duplicate of {payload.duplicate_reference}", actor=admin.email)
    await db.commit()
    return {"status": "duplicate", "reference": payload.duplicate_reference}
