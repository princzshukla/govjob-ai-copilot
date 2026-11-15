"""Layer 1 source health: 'ok' → 'degraded' → 'recovered' lifecycle.

Deterministic, DB-backed (no network): the fetch layer is stubbed, alerts are
captured, and the transitions on ``scrape_sources.status`` are asserted.
A degraded source keeps polling (with backoff) so recovery is detected
automatically; a robots.txt-disallowed source is hard-disabled instead.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import delete

from app.core.database import AsyncSessionLocal
from app.models.pipeline import ScrapeLog, ScrapeSource
from app.services import layer1_poller as lp


def _source(suffix: str) -> ScrapeSource:
    return ScrapeSource(
        slug=f"test-status-{suffix}",
        name="Test Commission",
        url="https://example.gov.in/",
        tier=1,
        fetch_mode="httpx",
        css_selector=None,
        interval_seconds=120,
        enabled=True,
    )


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session
        await session.close()


@pytest.fixture
async def cleanup(db):
    ids: list[int] = []
    yield ids
    if ids:
        await db.execute(delete(ScrapeLog).where(ScrapeLog.source_id.in_(ids)))
        await db.execute(delete(ScrapeSource).where(ScrapeSource.id.in_(ids)))
        await db.commit()


async def test_degrades_at_threshold_then_recovers_on_success(db, cleanup, monkeypatch):
    source = _source(uuid4().hex[:8])
    db.add(source)
    await db.flush()
    cleanup.append(source.id)

    alerts: list[str] = []

    async def _capture(text: str) -> None:
        alerts.append(text)

    monkeypatch.setattr(lp, "_alert", _capture)

    async def _boom(src):
        raise RuntimeError("503 Service Unavailable")

    monkeypatch.setattr(lp, "fetch_content", _boom)

    # Two failures: still ok, at the edge.
    for _ in range(lp.FAILURE_ALERT_THRESHOLD - 1):
        await lp.poll_source(db, source)
    assert source.status == "ok"
    assert alerts == []

    # Threshold failure flips it to degraded, exactly one transition alert.
    await lp.poll_source(db, source)
    assert source.status == "degraded"
    assert source.consecutive_failures == lp.FAILURE_ALERT_THRESHOLD
    degraded_alerts = [a for a in alerts if "DEGRADED" in a]
    assert len(degraded_alerts) == 1
    assert "test-status-" in degraded_alerts[0]

    # Further failures: no repeated alerts.
    await lp.poll_source(db, source)
    assert source.status == "degraded"
    assert len([a for a in alerts if "DEGRADED" in a]) == 1

    # Next successful poll flips it back and reports recovery.
    async def _ok(src):
        return ("fingerprint-v1", [], {}, {})

    monkeypatch.setattr(lp, "fetch_content", _ok)
    outcome = await lp.poll_source(db, source)
    assert outcome.ok is True
    assert source.status == "ok"
    assert source.consecutive_failures == 0
    assert any("recovered" in a for a in alerts)


async def test_not_modified_also_recovers(db, cleanup, monkeypatch):
    source = _source(uuid4().hex[:8])
    source.status = "degraded"
    source.consecutive_failures = lp.FAILURE_ALERT_THRESHOLD + 1
    db.add(source)
    await db.flush()
    cleanup.append(source.id)

    alerts: list[str] = []

    async def _capture(text: str) -> None:
        alerts.append(text)

    monkeypatch.setattr(lp, "_alert", _capture)

    async def _not_modified(src):
        raise lp.NotModified()

    monkeypatch.setattr(lp, "fetch_content", _not_modified)

    outcome = await lp.poll_source(db, source)
    assert outcome.ok is True
    assert source.status == "ok"
    assert source.consecutive_failures == 0
    assert any("recovered" in a for a in alerts)


async def test_robots_disallow_hard_disables(db, cleanup, monkeypatch):
    source = _source(uuid4().hex[:8])
    db.add(source)
    await db.flush()
    cleanup.append(source.id)

    alerts: list[str] = []

    async def _capture(text: str) -> None:
        alerts.append(text)

    async def _deny(url: str) -> bool:
        return False

    monkeypatch.setattr(lp, "_alert", _capture)
    monkeypatch.setattr(lp, "_robots_allows", _deny)

    outcome = await lp.poll_source(db, source)
    assert outcome.ok is False
    assert source.enabled is False
    assert source.status == "disabled"
    assert outcome.note == "robots-disallowed"


async def test_zero_link_runs_do_not_degrade(db, cleanup, monkeypatch):
    source = _source(uuid4().hex[:8])
    db.add(source)
    await db.flush()
    cleanup.append(source.id)

    async def _noop(text: str) -> None:
        pass

    monkeypatch.setattr(lp, "_alert", _noop)

    async def _empty(src):
        return ("fingerprint-v1", [], {}, {})

    monkeypatch.setattr(lp, "fetch_content", _empty)

    for _ in range(lp.FAILURE_ALERT_THRESHOLD + 2):
        await lp.poll_source(db, source)
    # zero runs accumulate for the zero-link alert, but status stays ok
    assert source.status == "ok"
    assert source.consecutive_zero_runs > 0
