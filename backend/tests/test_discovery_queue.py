"""DB-backed discovery queue / admin review tests."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.core import admit_cards as ac
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_session_token
from app.models.auth import Session, User
from app.models.admit_card import AdmitCardNotification
from app.models.discovery import DiscoveryHistory, NotificationDiscovery
from app.services import discovery_engine as de

ADMIN_EMAIL = "discovery-admin@example.com"


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


async def _admin_token(db) -> str:
    user = User(email=ADMIN_EMAIL, full_name="Discovery Admin", password_hash="unused")
    db.add(user)
    await db.flush()
    token = f"tok-{uuid4().hex}"
    db.add(Session(user_id=user.id, token_hash=hash_session_token(token),
                   expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc)))
    await db.commit()
    return token


def _make_entry(url: str, title: str):
    from app.services.coverage_watchdog import CoverageEntry

    return CoverageEntry(title=title, url=url, last_date=None)


class _NoopClient:
    async def head(self, *a, **kw):
        raise AssertionError("network not expected in these tests")

    async def get(self, *a, **kw):
        raise AssertionError("network not expected in these tests")


@pytest.fixture
async def cleanup_discovery(monkeypatch, tmp_path):
    overlay = tmp_path / "approved.json"
    monkeypatch.setattr(ac, "APPROVED_SEED_PATH", overlay)
    monkeypatch.setattr(ac, "SEED_ADMIT_CARDS", list(ac.SEED_ADMIT_CARDS))
    monkeypatch.setattr(settings, "ADMIN_EMAILS", ADMIN_EMAIL)
    yield
    async with AsyncSessionLocal() as db:
        await db.execute(delete(DiscoveryHistory))
        await db.execute(delete(NotificationDiscovery))
        await db.execute(delete(Session))
        await db.execute(delete(User).where(User.email == ADMIN_EMAIL))
        await db.execute(delete(AdmitCardNotification).where(AdmitCardNotification.id.like("disc-%")))
        await db.commit()


async def test_duplicate_aggregator_entries_create_one_row(db, cleanup_discovery):
    entry = _make_entry(f"https://agg.example/{uuid4().hex}", "Some Board Admit Card 2026")
    first = await de.process_entry(db, entry, _NoopClient())
    await db.commit()
    second = await de.process_entry(db, entry, _NoopClient())
    assert first is not None
    assert second is None
    rows = (await db.execute(select(NotificationDiscovery))).scalars().all()
    assert len(rows) == 1


async def test_admin_rejects_and_refuses_unverified_approval(client, db, cleanup_discovery):
    token = await _admin_token(db)
    record = NotificationDiscovery(
        aggregator_title="Unverified Notice Admit Card 2026",
        aggregator_url=f"https://agg.example/{uuid4().hex}",
        discovery_status=de.STATUS_NEEDS_REVIEW, verification_status="unverified",
    )
    db.add(record)
    await db.commit()

    resp = await client.post(f"/api/v1/admin/discoveries/{record.id}/approve", cookies={"session_id": token})
    assert resp.status_code == 422
    resp = await client.post(f"/api/v1/admin/discoveries/{record.id}/reject", cookies={"session_id": token})
    assert resp.status_code == 200
    resp = await client.post(f"/api/v1/admin/discoveries/{record.id}/approve", cookies={"session_id": token})
    assert resp.status_code == 409
    await db.refresh(record)
    assert record.discovery_status == de.STATUS_REJECTED


async def test_admin_approval_is_idempotent_and_preserves_null_dates(client, db, cleanup_discovery):
    token = await _admin_token(db)
    record = NotificationDiscovery(
        aggregator_title="Verified Board Admit Card 2026",
        aggregator_url=f"https://agg.example/{uuid4().hex}",
        organization="ssc", recruitment_year="2026", notice_subtype="admit_card",
        discovery_status=de.STATUS_PDF_VERIFIED, verification_status="official_evidence",
        official_pdf_url=f"https://ssc.gov.in/{uuid4().hex}.pdf",
        extracted_information={"analysis": de.analyze_entry("Verified Board Admit Card 2026")},
    )
    db.add(record)
    await db.commit()

    resp = await client.post(f"/api/v1/admin/discoveries/{record.id}/approve", cookies={"session_id": token})
    assert resp.status_code == 200, resp.text
    seed_id = resp.json()["seed_id"]
    assert seed_id == f"disc-{record.id}"

    overlay = json.loads(ac.APPROVED_SEED_PATH.read_text(encoding="utf-8"))
    assert len(overlay) == 1
    assert overlay[0]["notification_date"] is None and overlay[0]["exam_date"] is None

    card = (await db.execute(select(AdmitCardNotification).where(AdmitCardNotification.id == seed_id))).scalar_one_or_none()
    assert card is not None
    assert card.notification_date is None and card.exam_date is None

    resp = await client.post(f"/api/v1/admin/discoveries/{record.id}/approve", cookies={"session_id": token})
    assert resp.status_code == 409  # already approved

    history = (await db.execute(select(DiscoveryHistory).where(DiscoveryHistory.discovery_id == record.id))).scalars().all()
    assert any(h.to_status == de.STATUS_APPROVED for h in history)
