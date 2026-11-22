# app/api/v1/endpoints/admit_cards.py
"""Admit cards — official download links for exam-city intimations / e-admit cards.

Read-only listing of ``admit_cards`` rows. Deliberately separate from
``/eligibility/exams``: admit cards carry no eligibility constraints, and
their validity window is anchored to ``exam_date``, not an application
deadline. See app/models/admit_card.py.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.seo import id_prefix_from_slug
from app.core.timeutils import today_ist
from app.models.admit_card import AdmitCardNotification

router = APIRouter(prefix="/admit-cards", tags=["Admit Cards"])


def _admit_card_item(card: AdmitCardNotification) -> dict:
    item = {c.name: getattr(card, c.name) for c in AdmitCardNotification.__table__.columns}
    today = today_ist()
    if card.exam_date is None:
        state = "unknown"  # exam date not published — never treat as expired
    elif card.exam_date >= today:
        state = "upcoming"
    else:
        state = "over"
    item["exam_state"] = state
    return item


@router.get("")
async def list_admit_cards(
    response: Response,
    db: AsyncSession = Depends(get_db),
    subtype: str | None = Query(default=None, pattern="^(admit_card|exam_city)$"),
):
    """List currently useful admit cards (active + not older than 60 days).

    Rows stay active past exam day until the expiry task flips them; a card
    is shown while it is plausibly useful for the exam, so the cutoff is
    ``exam_date >= today`` (or unknown), with a 60-day backstop on
    ``notification_date`` when no exam date was published.
    """
    today = today_ist()
    cutoff = today - timedelta(days=60)
    stmt = (
        select(AdmitCardNotification)
        .where(
            AdmitCardNotification.is_active.is_(True),
            *([AdmitCardNotification.notice_subtype == subtype] if subtype else []),
            or_(
                AdmitCardNotification.exam_date >= today,
                AdmitCardNotification.exam_date.is_(None),
            ),
            or_(
                AdmitCardNotification.notification_date.is_(None),
                AdmitCardNotification.notification_date >= cutoff,
            ),
        )
        .order_by(
            AdmitCardNotification.notification_date.desc().nulls_last(),
            AdmitCardNotification.exam_date.asc().nulls_last(),
        )
    )
    cards = list((await db.execute(stmt)).scalars().all())
    response.headers["Cache-Control"] = "public, s-maxage=300, stale-while-revalidate=600"
    return {"total": len(cards), "admit_cards": [_admit_card_item(c) for c in cards]}


@router.get("/{key}")
async def get_admit_card_by_key(
    key: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """One admit-card notice by its public URL key."""
    prefix = id_prefix_from_slug(key)
    if prefix is None:
        raise HTTPException(status_code=404, detail="Admit card not found")
    normalised_id = func.replace(
        func.replace(func.lower(AdmitCardNotification.id), "-", ""), "_", ""
    )
    row = (
        await db.execute(select(AdmitCardNotification).where(normalised_id.startswith(prefix)))
    ).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Admit card not found")
    response.headers["Cache-Control"] = "public, s-maxage=300, stale-while-revalidate=600"
    return _admit_card_item(row)
