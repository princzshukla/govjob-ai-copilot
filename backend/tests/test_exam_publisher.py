"""Layer 2 → Layer 3 publish gate: deterministic DB tests (no network).

Covers the trust semantics of ``app.services.exam_publisher``:

* status='auto' rows with complete, plausible data are promoted into
  ``exam_notifications`` with official-PDF provenance, and the extraction /
  link rows are wired forward.
* 'auto' rows missing a required value are **held** (flipped to 'review' with
  an explicit machine-readable reason) — never published with invented data.
* Re-running is idempotent; 'review' rows are untouched; qualification →
  allowed_degrees/allowed_streams mapping handles degree wording, the
  "any graduate" fallback, and the unmappable case.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select

from app.core.database import AsyncSessionLocal
from app.models.exam import ExamNotification
from app.models.pipeline import ExtractionResult, RawDiscoveredLink, ScrapeSource
from app.services.exam_publisher import (
    build_exam_notification,
    degrees_and_streams_from_text,
    publish_auto_extractions,
)


def _extraction(**overrides):
    data = {
        "total_vacancies": 120,
        "min_age": 18,
        "age_max_general": 30,
        "age_relaxations": {"SC": 5, "OBC": 3},
        "age_cutoff_date": "2026-08-01",
        "required_qualification": "B.Tech (Computer Science / IT)",
        "application_last_date": "2026-09-30",
        "pay_level": "Level 4",
    }
    data.update(overrides)
    return ExtractionResult(
        status="auto",
        provider="test",
        extracted=data,
        field_confidence={},
        evidence={},
        missing_fields=[],
    )


async def _make_source_and_link(db, suffix: str, *, title: str | None, published_at=None):
    source = ScrapeSource(
        slug=f"test-src-{suffix}",
        name="Test Commission",
        url="https://example.gov.in/",
        tier=1,
        fetch_mode="httpx",
        config={"organizing_body": "Test Commission"},
    )
    db.add(source)
    await db.flush()
    link = RawDiscoveredLink(
        source_id=source.id,
        url=f"https://example.gov.in/advts/{suffix}.pdf",
        title=title,
        status="new",
        published_at=published_at,
        dedup_key=f"t-{suffix}",
    )
    db.add(link)
    await db.flush()
    return source, link


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


async def _cleanup(db, source_ids: list[int], exam_ids: list[str]):
    await db.execute(delete(ExtractionResult).where(ExtractionResult.raw_link_id.in_(
        select(RawDiscoveredLink.id).where(RawDiscoveredLink.source_id.in_(source_ids or [0]))
    )))
    await db.execute(delete(RawDiscoveredLink).where(RawDiscoveredLink.source_id.in_(source_ids or [0])))
    await db.execute(delete(ScrapeSource).where(ScrapeSource.id.in_(source_ids or [0])))
    if exam_ids:
        await db.execute(delete(ExamNotification).where(ExamNotification.id.in_(exam_ids)))
    await db.commit()


def test_degrees_and_streams_from_text():
    degrees, streams = degrees_and_streams_from_text("B.Tech (Computer Science / IT)")
    assert degrees == ["B.Tech"]
    assert streams == ["computer science", "information technology"]

    degrees, streams = degrees_and_streams_from_text("Any Graduate from a recognized University")
    assert degrees == ["Any Graduate"]

    degrees, streams = degrees_and_streams_from_text("Graduation in any discipline")
    assert degrees == ["Any Graduate"]

    degrees, streams = degrees_and_streams_from_text("Degree (Graduation) in any discipline")
    assert degrees == ["Any Graduate"]

    degrees, streams = degrees_and_streams_from_text("Ph.D in Quantum Entanglement")
    assert degrees == []


async def test_auto_row_is_promoted_with_provenance(db):
    suffix = uuid4().hex[:8]
    source_ids, exam_ids = [], []
    try:
        source, link = await _make_source_and_link(
            db, suffix, title="Test Advt 42-2026",
            published_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        )
        source_ids.append(source.id)
        extraction = _extraction()
        extraction.raw_link_id = link.id
        db.add(extraction)
        await db.commit()

        report = await publish_auto_extractions(db)
        assert len(report.published) == 1
        assert len(report.held) == 0
        outcome = report.published[0]

        exam = (
            await db.execute(select(ExamNotification).where(ExamNotification.id == outcome.exam_id))
        ).scalar_one()
        exam_ids.append(exam.id)
        assert exam.official_pdf_url == link.url
        assert exam.source_url == link.url
        assert exam.last_checked_at == date.today()
        assert exam.notification_date == date(2026, 8, 1)
        assert exam.application_deadline == date(2026, 9, 30)
        assert exam.min_age == 18 and exam.max_age_general == 30
        assert exam.age_cutoff_date == date(2026, 8, 1)
        assert exam.allowed_degrees == ["B.Tech"]
        assert exam.allowed_streams == ["computer science", "information technology"]
        assert exam.organizing_body == "Test Commission"
        assert exam.is_active is True

        await db.refresh(extraction)
        await db.refresh(link)
        assert extraction.exam_notification_id == exam.id
        assert extraction.status == "auto"
        assert link.status == "processed"
    finally:
        await _cleanup(db, source_ids, exam_ids)


async def test_missing_min_age_holds_row_no_exam_created(db):
    suffix = uuid4().hex[:8]
    source_ids, exam_ids = [], []
    try:
        source, link = await _make_source_and_link(db, suffix, title="Advt 43-2026")
        source_ids.append(source.id)
        extraction = _extraction(min_age=None)
        extraction.raw_link_id = link.id
        db.add(extraction)
        await db.commit()

        report = await publish_auto_extractions(db)
        assert len(report.published) == 0
        assert len(report.held) == 1
        assert "min_age" in report.held[0].detail

        await db.refresh(extraction)
        assert extraction.status == "review"
        assert "min_age" in (extraction.review_note or "")
        assert extraction.exam_notification_id is None
        count = (
            await db.execute(select(func.count()).select_from(ExamNotification).where(ExamNotification.id == f"ext-{extraction.id}"))
        ).scalar_one()
        assert count == 0
    finally:
        await _cleanup(db, source_ids, exam_ids)


async def test_unmappable_qualification_holds_row(db):
    suffix = uuid4().hex[:8]
    source_ids, exam_ids = [], []
    try:
        source, link = await _make_source_and_link(db, suffix, title="Advt 44-2026")
        source_ids.append(source.id)
        extraction = _extraction(required_qualification="Ph.D in Quantum Entanglement")
        extraction.raw_link_id = link.id
        db.add(extraction)
        await db.commit()

        report = await publish_auto_extractions(db)
        assert len(report.published) == 0
        assert len(report.held) == 1
        assert "no known degree" in report.held[0].detail
    finally:
        await _cleanup(db, source_ids, exam_ids)


async def test_graduation_only_qualification_maps_to_any_graduate(db):
    suffix = uuid4().hex[:8]
    source_ids, exam_ids = [], []
    try:
        source, link = await _make_source_and_link(db, suffix, title="Advt 45-2026")
        source_ids.append(source.id)
        extraction = _extraction(required_qualification="Graduation in any discipline from a University recognised by the Govt. of India")
        extraction.raw_link_id = link.id
        db.add(extraction)
        await db.commit()

        report = await publish_auto_extractions(db)
        assert len(report.published) == 1
        exam_ids.append(report.published[0].exam_id)
        exam = (
            await db.execute(select(ExamNotification).where(ExamNotification.id == exam_ids[0]))
        ).scalar_one()
        assert exam.allowed_degrees == ["Any Graduate"]
    finally:
        await _cleanup(db, source_ids, exam_ids)


async def test_review_rows_and_already_promoted_rows_are_untouched(db):
    suffix = uuid4().hex[:8]
    source_ids, exam_ids = [], []
    try:
        source, link = await _make_source_and_link(db, suffix, title="Advt 46-2026")
        source_ids.append(source.id)
        review_row = _extraction()
        review_row.status = "review"
        review_row.raw_link_id = link.id
        db.add(review_row)
        await db.commit()

        report = await publish_auto_extractions(db)
        assert report.total_considered == 0

        # Idempotency: publish once, then again — second run must be a no-op.
        link2_source, link2 = await _make_source_and_link(db, suffix + "b", title="Advt 47-2026")
        source_ids.append(link2_source.id)
        auto_row = _extraction()
        auto_row.raw_link_id = link2.id
        db.add(auto_row)
        await db.commit()

        first = await publish_auto_extractions(db)
        assert len(first.published) == 1
        exam_ids.append(first.published[0].exam_id)
        second = await publish_auto_extractions(db)
        assert second.total_considered == 0
    finally:
        await _cleanup(db, source_ids, exam_ids)


async def test_dry_run_writes_nothing(db):
    suffix = uuid4().hex[:8]
    source_ids, exam_ids = [], []
    try:
        source, link = await _make_source_and_link(db, suffix, title="Advt 48-2026")
        source_ids.append(source.id)
        extraction = _extraction()
        extraction.raw_link_id = link.id
        db.add(extraction)
        await db.commit()

        report = await publish_auto_extractions(db, dry_run=True)
        assert len(report.published) == 1

        await db.refresh(extraction)
        await db.refresh(link)
        assert extraction.exam_notification_id is None
        assert link.status == "new"
        count = (
            await db.execute(select(func.count()).select_from(ExamNotification).where(ExamNotification.id == f"ext-{extraction.id}"))
        ).scalar_one()
        assert count == 0
    finally:
        await _cleanup(db, source_ids, exam_ids)


def test_build_exam_notification_carries_valid_apply_url():
    from types import SimpleNamespace

    link = SimpleNamespace(
        title="Advt 42-2026",
        published_at=None,
        url="https://example.gov.in/advt.pdf",
    )
    source = SimpleNamespace(name="Test Commission", config={"organizing_body": "Test Commission"})
    extraction = _extraction(apply_url="https://ibpsreg.ibps.in/")
    exam, problems = build_exam_notification(extraction, link, source)
    assert problems == []
    assert exam is not None
    assert exam.apply_url == "https://ibpsreg.ibps.in/"


def test_build_exam_notification_drops_invalid_apply_url():
    from types import SimpleNamespace

    link = SimpleNamespace(
        title="Advt 42-2026",
        published_at=None,
        url="https://example.gov.in/advt.pdf",
    )
    source = SimpleNamespace(name="Test Commission", config={"organizing_body": "Test Commission"})
    for bad in ("not-a-url", "ftp://example.com/x", "javascript:alert(1)", "ibpsreg.ibps.in", "https://"):
        extraction = _extraction(apply_url=bad)
        exam, problems = build_exam_notification(extraction, link, source)
        assert problems == [], bad
        assert exam is not None
        assert exam.apply_url is None, bad


def test_build_exam_notification_missing_apply_url_is_none():
    from types import SimpleNamespace

    link = SimpleNamespace(
        title="Advt 42-2026",
        published_at=None,
        url="https://example.gov.in/advt.pdf",
    )
    source = SimpleNamespace(name="Test Commission", config={"organizing_body": "Test Commission"})
    extraction = _extraction()
    exam, problems = build_exam_notification(extraction, link, source)
    assert problems == []
    assert exam is not None
    assert exam.apply_url is None
