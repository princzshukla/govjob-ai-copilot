# app/api/v1/endpoints/discovery.py
"""Admin review for the missing-notification discovery queue.

Research queue only: no record reaches approved without official evidence, and
approval writes through the existing SEED_ADMIT_CARDS + upsert_admit_cards()
path rather than a second publishing pipeline.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_admin
from app.core.admit_cards import record_approved_seed, upsert_admit_cards
from app.core.database import get_db
from app.core.timeutils import today_ist
from app.models.discovery import DiscoveryHistory, NotificationDiscovery
from app.services import coverage_watchdog as cw
from app.services import discovery_engine as de

router = APIRouter(prefix="/admin/discoveries", tags=["Admin: Discovery"])


class DuplicateRequest(BaseModel):
    duplicate_reference: str


def _item(record: NotificationDiscovery) -> dict:
    return {
        "id": record.id,
        "aggregator_title": record.aggregator_title,
        "aggregator_url": record.aggregator_url,
        "organization": record.organization,
        "recruitment_year": record.recruitment_year,
        "notice_subtype": record.notice_subtype,
        "official_website": record.official_website,
        "official_notification_url": record.official_notification_url,
        "official_pdf_url": record.official_pdf_url,
        "extracted_information": record.extracted_information or {},
        "confidence_score": record.confidence_score,
        "verification_status": record.verification_status,
        "discovery_status": record.discovery_status,
        "duplicate_reference": record.duplicate_reference,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


async def _get(db: AsyncSession, record_id: int) -> NotificationDiscovery:
    record = (
        await db.execute(select(NotificationDiscovery).where(NotificationDiscovery.id == record_id))
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discovery not found")
    return record


@router.get("")
async def list_discoveries(
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
    discovery_status: str | None = Query(default=None),
    organization: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    stmt = select(NotificationDiscovery)
    if discovery_status:
        stmt = stmt.where(NotificationDiscovery.discovery_status == discovery_status)
    if organization:
        stmt = stmt.where(NotificationDiscovery.organization == organization)
    rows = (await db.execute(stmt.order_by(NotificationDiscovery.id.desc()).limit(limit))).scalars().all()
    return {"total": len(rows), "discoveries": [_item(r) for r in rows]}


@router.get("/{record_id}")
async def get_discovery(record_id: int, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    return _item(await _get(db, record_id))


@router.get("/{record_id}/history")
async def discovery_history(record_id: int, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
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
async def scan_unmatched(db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    """Investigate current unmatched entries through the shared watchdog."""
    report = await cw.check_coverage(cw.ADMIT_CARD_URL, kind="admit_card")
    stats = await de.run_discovery(db, report.missing)
    return {"unmatched": len(report.missing), **stats}


@router.post("/{record_id}/approve")
async def approve_discovery(record_id: int, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    """Promote a verified discovery into the existing seed structure."""
    record = await _get(db, record_id)
    official_url = record.official_pdf_url or record.official_notification_url
    analysis = (record.extracted_information or {}).get("analysis") or {}
    reason = de.validate_approval(record)
    if reason:
        code = (status.HTTP_409_CONFLICT if reason.startswith("invalid status")
                else status.HTTP_422_UNPROCESSABLE_ENTITY)
        raise HTTPException(status_code=code, detail=f"Approval refused: {reason}")

    existing = await de.collect_existing(db, exclude_id=record.id)
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
        "title": record.aggregator_title[:255],
        "organizing_body": (record.organization or "Unknown").upper()[:100],
        "exam_name": None,
        "link_kind": "notice_pdf" if record.official_pdf_url else "notice_page",
        "notice_subtype": record.notice_subtype or "admit_card",
        "notification_date": None,  # missing dates stay null
        "exam_date": None,
        "admit_url": official_url,
        "source_url": official_url,
        "last_checked_at": today_ist(),
    }
    try:
        record_approved_seed(seed_item)
        await upsert_admit_cards(db)  # existing architecture, no second pipeline
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    previous = record.discovery_status
    record.discovery_status = de.STATUS_APPROVED
    await de.add_history(
        db, record, previous, de.STATUS_APPROVED,
        f"Approved by {admin.email}; seed {seed_id}; official evidence {official_url[:120]}",
        actor=admin.email,
    )
    await db.commit()
    await db.refresh(record)
    return {"status": "approved", "seed_id": seed_id, "record": _item(record)}


@router.post("/{record_id}/reject")
async def reject_discovery(record_id: int, db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    record = await _get(db, record_id)
    previous = record.discovery_status
    record.discovery_status = de.STATUS_REJECTED
    await de.add_history(db, record, previous, de.STATUS_REJECTED, "Rejected by admin", actor=admin.email)
    await db.commit()
    return {"status": "rejected", "id": record.id}


@router.post("/{record_id}/mark-duplicate")
async def mark_duplicate(record_id: int, payload: DuplicateRequest,
                         db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    record = await _get(db, record_id)
    previous = record.discovery_status
    record.discovery_status = de.STATUS_DUPLICATE
    record.duplicate_reference = payload.duplicate_reference
    await de.add_history(db, record, previous, de.STATUS_DUPLICATE,
                         f"Marked duplicate of {payload.duplicate_reference}", actor=admin.email)
    await db.commit()
    return {"status": "duplicate", "reference": payload.duplicate_reference}
