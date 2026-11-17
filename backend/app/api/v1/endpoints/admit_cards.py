# app/api/v1/endpoints/admit_cards.py
"""Admit cards — official download links for exam-city intimations / e-admit cards.

Read-only listing of ``admit_cards`` rows. Deliberately separate from
``/eligibility/exams``: admit cards carry no eligibility constraints, and
their validity window is anchored to ``exam_date``, not an application
deadline. See app/models/admit_card.py.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
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
async def list_admit_cards(db: AsyncSession = Depends(get_db)):
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
    return {"total": len(cards), "admit_cards": [_admit_card_item(c) for c in cards]}
