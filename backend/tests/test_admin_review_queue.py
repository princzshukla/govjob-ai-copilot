"""Admin review queue + publish-time email digest.

Covers: require_admin gating (401 anon, 403 non-admin), list held items,
approve (promoted through the gate), reject, edit-then-promote, and the
SMTP digest (mocked smtplib, env-flagged).
"""
from __future__ import annotations

import smtplib
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_session_token
from app.models.auth import Session, User
from app.models.exam import ExamNotification
from app.models.pipeline import ExtractionResult, RawDiscoveredLink, ScrapeSource
from app.services import mailer

PASSWORD = "correct-horse-battery"
ADMIN_EMAIL = "admin@example.com"
PLAIN_EMAIL = "plain@example.com"


async def _create_user_with_session(db, email: str) -> str:
    user = User(email=email, full_name="Test User", password_hash="unused")
    db.add(user)
    await db.flush()
    token = f"tok-{uuid4().hex}"
    db.add(
        Session(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        )
    )
    await db.commit()
    return token


def _extraction(suffix: str, **overrides) -> ExtractionResult:
    data = {
        "total_vacancies": 150,
        "min_age": 18,
        "age_max_general": 30,
        "age_relaxations": {"SC": 5},
        "age_cutoff_date": "2026-08-01",
        "required_qualification": "B.Tech (Computer Science)",
        "application_last_date": "2026-09-30",
        "pay_level": "Level 7",
    }
    data.update(overrides)
    return ExtractionResult(
        status="review",
        provider="test",
        extracted=data,
        field_confidence={},
        evidence={"pay_level": "Level- 7 in the Pay Matrix"},
        missing_fields=["pay_level"],
        review_note="missing critical fields: pay_level",
    )


async def _make_source_link_extraction(db, suffix: str, **overrides):
    source = ScrapeSource(
        slug=f"adm-{suffix}",
        name="Admin Test Commission",
        url="https://example.gov.in/",
        tier=1,
        fetch_mode="httpx",
        config={"organizing_body": "Admin Test Commission"},
    )
    db.add(source)
    await db.flush()
    link = RawDiscoveredLink(
        source_id=source.id,
        url=f"https://example.gov.in/advts/{suffix}.pdf",
        title=f"Admin Test Advt {suffix}",
        status="processed",
        published_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        dedup_key=f"adm-{suffix}",
    )
    db.add(link)
    await db.flush()
    extraction = _extraction(suffix, **overrides)
    extraction.raw_link_id = link.id
    db.add(extraction)
    await db.commit()
    return source, link, extraction


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def cleanup(db):
    exam_ids = []
    source_ids = []
    yield {"exams": exam_ids, "sources": source_ids}
    for exam_id in exam_ids:
        await db.execute(delete(ExamNotification).where(ExamNotification.id == exam_id))
    await db.execute(delete(RawDiscoveredLink).where(RawDiscoveredLink.source_id.in_(source_ids or [0])))
    await db.execute(delete(ScrapeSource).where(ScrapeSource.id.in_(source_ids or [0])))
    await db.execute(delete(Session))
    await db.execute(delete(User).where(User.email.in_([ADMIN_EMAIL, PLAIN_EMAIL])))
    await db.commit()


async def test_review_queue_requires_admin(db, cleanup, client, monkeypatch):
    suffix = uuid4().hex[:8]
    source, link, extraction = await _make_source_link_extraction(db, suffix)
    cleanup["sources"].append(source.id)

    # Anonymous → 401.
    resp = await client.get("/api/v1/admin/review-queue")
    assert resp.status_code == 401

    # Non-admin user → 403.
    token = await _create_user_with_session(db, PLAIN_EMAIL)
    resp = await client.get("/api/v1/admin/review-queue", cookies={"session_id": token})
    assert resp.status_code == 403

    # Admin → list with the held item.
    monkeypatch.setattr(settings, "ADMIN_EMAILS", ADMIN_EMAIL)
    token = await _create_user_with_session(db, ADMIN_EMAIL)
    resp = await client.get("/api/v1/admin/review-queue", cookies={"session_id": token})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    item = body[0]
    assert item["id"] == extraction.id
    assert item["url"] == link.url
    assert item["evidence"] == {"pay_level": "Level- 7 in the Pay Matrix"}
    assert item["review_note"] == "missing critical fields: pay_level"


async def test_approve_promotes_and_list_empties(db, cleanup, client, monkeypatch):
    suffix = uuid4().hex[:8]
    source, link, extraction = await _make_source_link_extraction(db, suffix)
    cleanup["sources"].append(source.id)
    cleanup["exams"].append(f"ext-{extraction.id}")
    monkeypatch.setattr(settings, "ADMIN_EMAILS", ADMIN_EMAIL)
    token = await _create_user_with_session(db, ADMIN_EMAIL)

    resp = await client.post(f"/api/v1/admin/review-queue/{extraction.id}/approve", cookies={"session_id": token})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "promoted"

    exam = (
        await db.execute(select(ExamNotification).where(ExamNotification.id == f"ext-{extraction.id}"))
    ).scalar_one()
    assert exam.official_pdf_url == link.url

    resp = await client.get("/api/v1/admin/review-queue", cookies={"session_id": token})
    assert resp.json() == []


async def test_reject_removes_from_queue(db, cleanup, client, monkeypatch):
    suffix = uuid4().hex[:8]
    source, link, extraction = await _make_source_link_extraction(db, suffix)
    cleanup["sources"].append(source.id)
    monkeypatch.setattr(settings, "ADMIN_EMAILS", ADMIN_EMAIL)
    token = await _create_user_with_session(db, ADMIN_EMAIL)

    resp = await client.post(f"/api/v1/admin/review-queue/{extraction.id}/reject", cookies={"session_id": token})
    assert resp.status_code == 200

    await db.refresh(extraction)
    assert extraction.status == "rejected"


async def test_edit_then_promote(db, cleanup, client, monkeypatch):
    suffix = uuid4().hex[:8]
    # min_age missing → the publish gate cannot promote until the admin fills it.
    source, link, extraction = await _make_source_link_extraction(db, suffix, min_age=None, missing_fields=["min_age"])
    extraction.extracted = {**extraction.extracted, "min_age": None}
    await db.commit()
    cleanup["sources"].append(source.id)
    cleanup["exams"].append(f"ext-{extraction.id}")
    monkeypatch.setattr(settings, "ADMIN_EMAILS", ADMIN_EMAIL)
    token = await _create_user_with_session(db, ADMIN_EMAIL)

    # Without min_age, approve must fail with 422 and keep the row in review.
    resp = await client.post(f"/api/v1/admin/review-queue/{extraction.id}/approve", cookies={"session_id": token})
    assert resp.status_code == 422, resp.text
    await db.refresh(extraction)
    assert extraction.status == "review"

    # The admin fills the gap; promotion now succeeds.
    resp = await client.post(
        f"/api/v1/admin/review-queue/{extraction.id}/edit",
        json={"min_age": 18},
        cookies={"session_id": token},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "promoted"


async def test_publish_sends_digest_when_configured(db, cleanup, client, monkeypatch):
    sent = []

    class _SMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            pass

        def login(self, user, password):
            pass

        def send_message(self, message):
            sent.append(message)

    monkeypatch.setattr(smtplib, "SMTP", _SMTP)
    monkeypatch.setattr(settings, "MAIL_PROVIDER", "smtp")
    monkeypatch.setattr(settings, "MAIL_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "MAIL_SMTP_USER", "u@example.com")
    monkeypatch.setattr(settings, "MAIL_SMTP_PASS", "secret")
    monkeypatch.setattr(settings, "MAIL_DIGEST_TO", "op@example.com")
    monkeypatch.setattr(settings, "MAIL_FROM", "GovJob <no-reply@example.com>")

    suffix = uuid4().hex[:8]
    source, link, extraction = await _make_source_link_extraction(db, suffix)
    cleanup["sources"].append(source.id)
    cleanup["exams"].append(f"ext-{extraction.id}")
    monkeypatch.setattr(settings, "ADMIN_EMAILS", ADMIN_EMAIL)
    token = await _create_user_with_session(db, ADMIN_EMAIL)

    resp = await client.post(f"/api/v1/admin/review-queue/{extraction.id}/approve", cookies={"session_id": token})
    assert resp.status_code == 200, resp.text

    assert len(sent) == 1
    assert "1 new exam" in sent[0]["Subject"]
    body = sent[0].get_content()
    assert "Admin Test Advt" in body or "Admin Test Commission" in body
    assert "example.gov.in" in body


async def test_mailer_inert_when_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "MAIL_PROVIDER", "")
    monkeypatch.setattr(settings, "MAIL_DIGEST_TO", "")
    assert mailer.mail_enabled() is False
    assert mailer.send_exam_digest([{"title": "T", "organizing_body": "B", "application_deadline": "2026-12-31", "official_pdf_url": "u"}]) is False
