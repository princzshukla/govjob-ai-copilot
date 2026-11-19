"""DB-backed Jobs Watchdog / discovery-queue / deadline audit tests."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.core import seed as seed_module
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_session_token
from app.models.auth import Session, User
from app.models.discovery import DiscoveryHistory, NotificationDiscovery
from app.models.exam import ExamNotification
from app.models.exam_changes import ExamNotificationChange, JobsWatchdogReport
from app.services import coverage_watchdog as cw
from app.services import discovery_engine as de
from app.services import job_deadline_watchdog as jdw
from app.services import jobs_report
from app.services import jobs_watchdog as jw

ADMIN_EMAIL = "jobs-watchdog-admin@example.com"


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


async def _admin_token(db) -> str:
    user = User(email=ADMIN_EMAIL, full_name="Jobs Admin", password_hash="unused")
    db.add(user)
    await db.flush()
    token = f"tok-{uuid4().hex}"
    db.add(Session(user_id=user.id, token_hash=hash_session_token(token),
                   expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc)))
    await db.commit()
    return token


def _verified_record(title: str, fields: dict | None = None) -> NotificationDiscovery:
    analysis = de.analyze_entry(title)
    return NotificationDiscovery(
        aggregator_title=title,
        aggregator_url=f"https://agg.example/{uuid4().hex}",
        organization="ssc", recruitment_year="2026", notice_subtype="recruitment",
        notification_kind="job", classification=jw.CLASS_NEW,
        discovery_status=de.STATUS_PDF_VERIFIED, verification_status="official_evidence",
        official_pdf_url=f"https://ssc.gov.in/{uuid4().hex}.pdf",
        extracted_information={"analysis": analysis, "fields": fields or {}},
    )


class _NoopClient:
    async def head(self, *a, **kw):
        raise AssertionError("network not expected")

    async def get(self, *a, **kw):
        raise AssertionError("network not expected")


@pytest.fixture
async def cleanup_jobs(monkeypatch, tmp_path):
    monkeypatch.setattr(seed_module, "APPROVED_JOB_SEED_PATH", tmp_path / "approved_jobs.json")
    monkeypatch.setattr(seed_module, "SEED_EXAMS", list(seed_module.SEED_EXAMS))
    monkeypatch.setattr(settings, "ADMIN_EMAILS", ADMIN_EMAIL)
    yield
    async with AsyncSessionLocal() as db:
        await db.execute(delete(DiscoveryHistory))
        await db.execute(delete(NotificationDiscovery).where(NotificationDiscovery.notification_kind == "job"))
        await db.execute(delete(JobsWatchdogReport))
        await db.execute(delete(ExamNotificationChange))
        await db.execute(delete(ExamNotification).where(ExamNotification.id.like("disc-%")))
        await db.execute(delete(ExamNotification).where(ExamNotification.id.like("deadline-test-%")))
        await db.execute(delete(Session))
        await db.execute(delete(User).where(User.email == ADMIN_EMAIL))
        await db.commit()


async def test_job_record_is_classified_and_idempotent(db, cleanup_jobs):
    entry = cw.CoverageEntry(title="SSC CGL 2026 Online Form",
                             url=f"https://agg.example/{uuid4().hex}", last_date=None)
    first = await de.process_entry(db, entry, _NoopClient(), notification_kind="job",
                                   classification=jw.CLASS_VERIFY)
    await db.commit()
    assert first is not None
    assert first.notification_kind == "job"
    assert first.classification == jw.CLASS_VERIFY
    assert (await de.process_entry(db, entry, _NoopClient(), notification_kind="job")) is None


async def test_unverified_job_approval_is_refused(client, db, cleanup_jobs):
    token = await _admin_token(db)
    record = NotificationDiscovery(
        aggregator_title="Unverified Recruitment 2026",
        aggregator_url=f"https://agg.example/{uuid4().hex}",
        notification_kind="job", discovery_status=de.STATUS_NEEDS_REVIEW,
        verification_status="unverified",
    )
    db.add(record)
    await db.commit()
    resp = await client.post(f"/api/v1/admin/job-discoveries/{record.id}/approve",
                             json={}, cookies={"session_id": token})
    assert resp.status_code == 422
    resp = await client.post(f"/api/v1/admin/job-discoveries/{record.id}/reject",
                             cookies={"session_id": token})
    assert resp.status_code == 200
    resp = await client.post(f"/api/v1/admin/job-discoveries/{record.id}/approve",
                             json={}, cookies={"session_id": token})
    assert resp.status_code == 409


async def test_verified_job_approval_writes_overlay_and_exam(client, db, cleanup_jobs):
    token = await _admin_token(db)
    fields = {
        "application_last_date": "2026-12-31",
        "application_start_date": "2026-11-01",
        "min_age": 18,
        "age_max_general": 27,
        "required_qualification": "Bachelor's degree in any discipline",
    }
    record = _verified_record("SSC Combined Graduate Level (CGL) 2026", fields)
    db.add(record)
    await db.commit()

    resp = await client.post(
        f"/api/v1/admin/job-discoveries/{record.id}/approve",
        json={"age_cutoff_date": "2026-10-01"},
        cookies={"session_id": token},
    )
    assert resp.status_code == 200, resp.text
    seed_id = resp.json()["seed_id"]
    overlay = json.loads(seed_module.APPROVED_JOB_SEED_PATH.read_text(encoding="utf-8"))
    assert len(overlay) == 1 and overlay[0]["id"] == seed_id
    exam = (await db.execute(select(ExamNotification).where(ExamNotification.id == seed_id))).scalar_one_or_none()
    assert exam is not None
    assert exam.application_deadline == date(2026, 12, 31)
    assert exam.application_start_date == date(2026, 11, 1)
    assert exam.verification_status == "verified"

    resp = await client.post(f"/api/v1/admin/job-discoveries/{record.id}/approve",
                             json={"age_cutoff_date": "2026-10-01"}, cookies={"session_id": token})
    assert resp.status_code == 409  # idempotent: no duplicate seed row


async def test_approval_is_held_when_required_fields_are_missing(client, db, cleanup_jobs):
    token = await _admin_token(db)
    record = _verified_record("SSC Combined Graduate Level (CGL) 2026", {})
    db.add(record)
    await db.commit()
    resp = await client.post(f"/api/v1/admin/job-discoveries/{record.id}/approve",
                             json={}, cookies={"session_id": token})
    assert resp.status_code == 422
    assert resp.json()["detail"]["reason"] == "missing_required_fields"
    await db.refresh(record)
    assert record.discovery_status == de.STATUS_PDF_VERIFIED  # still awaiting review


async def test_revised_deadline_is_audited_and_locks_the_seed_row(db, cleanup_jobs, monkeypatch):
    exam = ExamNotification(
        id="deadline-test-1", title="SSC Combined Graduate Level (CGL) 2026",
        organizing_body="SSC", application_deadline=date(2026, 11, 20),
        min_age=18, max_age_general=27, age_cutoff_date=date(2026, 8, 1),
        allowed_degrees=["Any Graduate"], source_url="https://ssc.gov.in/notice.pdf",
        is_active=True,
    )
    db.add(exam)
    await db.commit()
    text = (
        "SSC Combined Graduate Level (CGL) 2026\n"
        "Last Date: 25 December 2026\n"
        "Starting Date: 01.11.2026\n"
    )

    async def fake_fetch(url, client_):
        return text, True

    monkeypatch.setattr(jdw, "_fetch_notice_text", fake_fetch)
    stats = await jdw.check_exam_deadlines(db)
    assert stats["updated"] >= 1
    await db.refresh(exam)
    assert exam.application_deadline == date(2026, 12, 25)
    assert exam.application_start_date == date(2026, 11, 1)
    assert exam.deadline_locked is True
    assert exam.verification_status == "verified"
    change = (await db.execute(select(ExamNotificationChange).where(
        ExamNotificationChange.exam_id == exam.id))).scalars().first()
    assert change is not None
    assert change.change_kind == "deadline_extended"
    assert change.old_value == "2026-11-20" and change.new_value == "2026-12-25"


async def test_cancelled_notice_deactivates_and_audits(db, cleanup_jobs, monkeypatch):
    exam = ExamNotification(
        id="deadline-test-2", title="SSC Combined Graduate Level (CGL) 2026",
        organizing_body="SSC", application_deadline=date(2026, 12, 25),
        min_age=18, max_age_general=27, age_cutoff_date=date(2026, 8, 1),
        allowed_degrees=["Any Graduate"], source_url="https://ssc.gov.in/notice.pdf",
        is_active=True,
    )
    db.add(exam)
    await db.commit()

    async def fake_fetch(url, client_):
        return "SSC Combined Graduate Level (CGL) 2026 — this recruitment is cancelled.", True

    monkeypatch.setattr(jdw, "_fetch_notice_text", fake_fetch)
    await jdw.check_exam_deadlines(db)
    await db.refresh(exam)
    assert exam.is_active is False
    change = (await db.execute(select(ExamNotificationChange).where(
        ExamNotificationChange.exam_id == exam.id))).scalars().first()
    assert change.change_kind == "cancelled"


async def test_locked_deadline_is_not_overwritten_by_seed_upsert(db, cleanup_jobs, monkeypatch):
    exam = ExamNotification(
        id="deadline-test-3", title="SSC Combined Graduate Level (CGL) 2026",
        organizing_body="SSC", application_deadline=date(2026, 12, 25),
        min_age=18, max_age_general=27, age_cutoff_date=date(2026, 8, 1),
        allowed_degrees=["Any Graduate"], source_url="https://ssc.gov.in/official.pdf",
        is_active=False, deadline_locked=True,
    )
    db.add(exam)
    await db.commit()
    monkeypatch.setattr(seed_module, "SEED_EXAMS", [{
        "id": exam.id, "title": exam.title, "organizing_body": "SSC",
        "application_deadline": date(2026, 10, 1), "min_age": 18,
        "max_age_general": 27, "age_cutoff_date": date(2026, 8, 1),
        "allowed_degrees": ["Any Graduate"], "official_pdf_url": "https://stale.example/pdf",
    }])
    await seed_module.upsert_seed_exams(db)
    await db.refresh(exam)
    assert exam.application_deadline == date(2026, 12, 25)
    assert exam.is_active is False  # seed must not reopen a locked row
    assert exam.source_url == "https://ssc.gov.in/official.pdf"


async def test_report_counts_are_explicit_and_persisted(db, cleanup_jobs):
    report = cw.CoverageReport(
        source_url="https://agg.example/latest-jobs/",
        entries=[cw.CoverageEntry("A", "u1", None), cw.CoverageEntry("B", "u2", None)],
        matched=[], missing=[cw.CoverageEntry("B", "u2", None)], seed_count=87,
        duplicate_matches={"A": ["A again"]},
        ambiguous=[(cw.CoverageEntry("C", "u3", None), "seed", 0.72)],
    )
    data = await jobs_report.build_jobs_watchdog_report(db, report, {"pdf_verified": 2}, {"updated": 1})
    assert data["total_live"] == 2 and data["total_seeds"] == 87
    assert data["unmatched"] == 1 and data["duplicate_candidates"] == 1
    assert data["ambiguous"] == 1 and data["official_pdfs_verified"] == 2
    assert data["honest"] is False
    row = (await db.execute(select(JobsWatchdogReport))).scalar_one_or_none()
    assert row is not None and row.payload == data
