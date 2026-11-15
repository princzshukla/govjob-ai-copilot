"""Layer 2 worker: drain → extract → gate → publish/review, with safety rails.

Deterministic: PDF download is stubbed, the extractor is stubbed, and the
token budget is driven through the same code path the CLI uses.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models.exam import ExamNotification
from app.models.pipeline import (
    ExtractionResult,
    RawDiscoveredLink,
    ScrapeLog,
    ScrapeSource,
    TokenBudget,
)
from app.schemas.pipeline import ExtractionResult as ExtractionSchema
from app.services import layer2_worker as lw
from app.services import notification_extractor as nx


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def cleanup(db):
    ids: list[int] = []
    exam_ids: list[str] = []
    yield {"sources": ids, "exams": exam_ids}
    if ids:
        sub = select(RawDiscoveredLink.id).where(RawDiscoveredLink.source_id.in_(ids))
        await db.execute(delete(ExtractionResult).where(ExtractionResult.raw_link_id.in_(sub)))
        await db.execute(delete(RawDiscoveredLink).where(RawDiscoveredLink.source_id.in_(ids)))
        await db.execute(delete(ScrapeLog).where(ScrapeLog.source_id.in_(ids)))
        await db.execute(delete(ScrapeSource).where(ScrapeSource.id.in_(ids)))
        if exam_ids:
            await db.execute(delete(ExamNotification).where(ExamNotification.id.in_(exam_ids)))
        await db.execute(delete(TokenBudget))
        await db.commit()


async def _make_source_and_links(db, suffix: str, n_links: int = 2):
    source = ScrapeSource(
        slug=f"test-worker-{suffix}",
        name="Test Commission",
        url="https://example.gov.in/",
        tier=1,
        fetch_mode="httpx",
        config={"organizing_body": "Test Commission"},
    )
    db.add(source)
    await db.flush()
    links = []
    for i in range(n_links):
        link = RawDiscoveredLink(
            source_id=source.id,
            url=f"https://example.gov.in/advts/{suffix}-{i}.pdf",
            title=f"Test Advt {suffix}-{i}",
            status="new",
            published_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
            dedup_key=f"tw-{suffix}-{i}",
        )
        db.add(link)
        links.append(link)
    await db.commit()
    return source, links


def _auto_result() -> ExtractionSchema:
    return ExtractionSchema(
        total_vacancies=150,
        min_age=20,
        age_max_general=30,
        age_relaxations={"SC": 5},
        age_cutoff_date=date(2026, 8, 1),
        required_qualification="B.Tech (Computer Science)",
        application_last_date=date(2026, 9, 30),
        pay_level="Level 7",
        field_confidence={f: 0.9 for f in nx.CRITICAL_FIELDS},
        evidence={},
        confidence=0.9,
        raw_text_chars=500,
        is_scanned=False,
        needs_manual_review=False,
        review_reasons=[],
        provider="groq",
    )


def _review_result() -> ExtractionSchema:
    r = _auto_result()
    r.needs_manual_review = True
    r.review_reasons = ["missing critical fields: pay_level"]
    r.pay_level = None
    r.confidence = 0.0
    return r


def _stub(monkeypatch, *, auto: bool = True, est: float = 100.0):
    async def fake_fetch(url, *args, **kwargs):
        return b"%PDF-1.4 fake"

    monkeypatch.setattr(lw, "_fetch_pdf", fake_fetch)
    monkeypatch.setattr(nx, "extract_text_stats", lambda b: ("vacancy text " * 60, 1, 500.0))

    async def fake_extract(pdf_bytes, *, use_cache=True):
        return _auto_result() if auto else _review_result()

    monkeypatch.setattr(nx, "extract_notification", fake_extract)
    monkeypatch.setattr(lw, "_estimate_doc_tokens", lambda chars: est)


async def test_auto_link_flows_to_exam_notification(db, cleanup, monkeypatch):
    suffix = uuid4().hex[:8]
    source, links = await _make_source_and_links(db, suffix, n_links=2)
    cleanup["sources"].append(source.id)
    _stub(monkeypatch, auto=True)

    stats = await lw.process_new_links((source.slug,), max_docs=10)
    assert stats.auto == 2
    assert stats.downloaded == 2

    for link in links:
        await db.refresh(link)
        assert link.status == "processed"
        assert link.process_attempts == 1

    rows = (
        await db.execute(select(ExtractionResult).where(ExtractionResult.raw_link_id.in_([l.id for l in links])))
    ).scalars().all()
    assert len(rows) == 2
    assert {r.status for r in rows} == {"auto"}

    exams = (
        await db.execute(select(ExamNotification).where(ExamNotification.organizing_body == "Test Commission"))
    ).scalars().all()
    assert len(exams) == 2
    cleanup["exams"].extend(e.id for e in exams)
    assert {e.official_pdf_url for e in exams} == {l.url for l in links}

    budget = (await db.execute(select(TokenBudget))).scalars().all()
    assert len(budget) == 1
    assert budget[0].tokens_used > 0


async def test_review_link_stays_in_review_queue(db, cleanup, monkeypatch):
    suffix = uuid4().hex[:8]
    source, links = await _make_source_and_links(db, suffix, n_links=1)
    cleanup["sources"].append(source.id)
    _stub(monkeypatch, auto=False)

    stats = await lw.process_new_links((source.slug,), max_docs=10)
    assert stats.review == 1
    assert stats.auto == 0

    link = links[0]
    await db.refresh(link)
    assert link.status == "processed"

    row = (
        await db.execute(select(ExtractionResult).where(ExtractionResult.raw_link_id == link.id))
    ).scalar_one()
    assert row.status == "review"
    assert row.extracted["review_reasons"] == ["missing critical fields: pay_level"]
    exams = (
        await db.execute(select(ExamNotification).where(ExamNotification.organizing_body == "Test Commission"))
    ).scalars().all()
    assert exams == []


async def test_daily_budget_stops_worker_cleanly(db, cleanup, monkeypatch):
    suffix = uuid4().hex[:8]
    source, links = await _make_source_and_links(db, suffix, n_links=3)
    cleanup["sources"].append(source.id)
    monkeypatch.setenv("WORKER_DAILY_TOKEN_BUDGET", "150")
    _stub(monkeypatch, auto=True, est=100.0)

    stats = await lw.process_new_links((source.slug,), max_docs=10)
    # doc 1 consumes the budget; doc 2 must stop the worker
    assert stats.downloaded == 1
    assert stats.budget_stopped is True
    remaining = (
        await db.execute(select(RawDiscoveredLink).where(RawDiscoveredLink.source_id == source.id, RawDiscoveredLink.status == "new"))
    ).scalars().all()
    assert len(remaining) == 2


async def test_download_failure_increments_attempts(db, cleanup, monkeypatch):
    suffix = uuid4().hex[:8]
    source, links = await _make_source_and_links(db, suffix, n_links=1)
    cleanup["sources"].append(source.id)

    async def _boom(url, *args, **kwargs):
        raise RuntimeError("503 Service Unavailable")

    monkeypatch.setattr(lw, "_fetch_pdf", _boom)

    stats = await lw.process_new_links((source.slug,), max_docs=10)
    assert stats.failed == 1
    link = links[0]
    await db.refresh(link)
    assert link.process_attempts == 1
    assert link.status == "new"


async def test_non_pdf_is_ignored_without_llm(db, cleanup, monkeypatch):
    suffix = uuid4().hex[:8]
    source, links = await _make_source_and_links(db, suffix, n_links=1)
    cleanup["sources"].append(source.id)

    async def _none(url, *args, **kwargs):
        return None

    monkeypatch.setattr(lw, "_fetch_pdf", _none)

    async def _must_not_call(pdf_bytes, *, use_cache=True):
        raise AssertionError("extractor must not run for non-PDFs")

    monkeypatch.setattr(nx, "extract_notification", _must_not_call)

    stats = await lw.process_new_links((source.slug,), max_docs=10)
    assert stats.ignored == 1
    link = links[0]
    await db.refresh(link)
    assert link.status == "ignored"


async def test_dry_run_never_calls_llm(db, cleanup, monkeypatch):
    suffix = uuid4().hex[:8]
    source, links = await _make_source_and_links(db, suffix, n_links=2)
    cleanup["sources"].append(source.id)

    async def _fetch(url, *a, **kw):
        return b"%PDF-1.4 fake"

    monkeypatch.setattr(lw, "_fetch_pdf", _fetch)
    monkeypatch.setattr(nx, "extract_text_stats", lambda b: ("vacancy text " * 60, 1, 500.0))

    async def _must_not_call(pdf_bytes, *, use_cache=True):
        raise AssertionError("extractor must not run in --dry-run")

    monkeypatch.setattr(nx, "extract_notification", _must_not_call)

    stats = await lw.process_new_links((source.slug,), max_docs=10, dry_run=True)
    assert stats.downloaded == 2

    for link in links:
        await db.refresh(link)
        assert link.status == "new"  # untouched
    rows = (
        await db.execute(select(ExtractionResult).where(ExtractionResult.raw_link_id.in_([l.id for l in links])))
    ).scalars().all()
    assert rows == []


async def test_link_skipped_after_three_failed_attempts(db, cleanup, monkeypatch):
    suffix = uuid4().hex[:8]
    source, links = await _make_source_and_links(db, suffix, n_links=1)
    cleanup["sources"].append(source.id)
    links[0].process_attempts = 3
    await db.commit()

    stats = await lw.process_new_links((source.slug,), max_docs=10)
    assert stats.skipped_attempts == 1
    assert stats.downloaded == 0
