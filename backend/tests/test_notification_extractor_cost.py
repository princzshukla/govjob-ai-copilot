"""PDF cost reduction: content-hash cache + per-field escalation tests.

* 'auto' extractions are cached by sha256(pdf_bytes) — a repeat call serves
  from cache without touching the LLM.
* 'review' verdicts are never cached (a review can become auto after the
  extractor improves).
* Missing/low-confidence criticals escalate ONLY those fields to the fallback
  provider (targeted small prompt), merging what the fallback fills with
  sufficient confidence — never the whole document as-is.
"""
from __future__ import annotations

import json
from uuid import uuid4

import pymupdf
import pytest
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models.pipeline import ExtractionCache
from app.services import notification_extractor as nx

# --- helpers ---------------------------------------------------------------

def _make_pdf(unique_text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    body = (
        "BHARAT HEAVY ELECTRICALS LIMITED — ANNUAL RECRUITMENT NOTIFICATION\n"
        "Advertisement No. 42-2026 — Engineer Trainee.\n"
        "AGE (AS ON 01.07.2026): Minimum 20 years, Maximum 30 years general.\n"
        "ELIGIBLE: Full-Time Bachelor's Degree in Engineering / Technology.\n"
        "Total 150 vacancies in Civil and Mechanical disciplines.\n"
        "Online Registration 01-07-2026 to 21-07-2026.\n"
        "Pay Level 7 in the Pay Matrix, initial basic Rs 50,000 + allowances.\n"
    ) * 3 + unique_text
    page.insert_text((50, 50), body)
    data = doc.tobytes()
    doc.close()
    return data


def _payload(**overrides):
    base = {
        "total_vacancies": {"value": 150, "confidence": 0.9, "evidence": "Total 150 vacancies"},
        "min_age": {"value": 20, "confidence": 0.9, "evidence": "Minimum 20 years"},
        "age_max_general": {"value": 30, "confidence": 0.9, "evidence": "Maximum 30 years"},
        "age_cutoff_date": {"value": "2026-07-01", "confidence": 0.9, "evidence": "AGE (AS ON 01.07.2026)"},
        "required_qualification": {"value": "B.Tech (Engineering/Technology)", "confidence": 0.9, "evidence": "Bachelor's Degree in Engineering / Technology"},
        "application_last_date": {"value": "2026-07-21", "confidence": 0.9, "evidence": "01-07-2026 to 21-07-2026"},
        "pay_level": {"value": "Level 7 (Rs 50,000)", "confidence": 0.9, "evidence": "Level 7 in the Pay Matrix"},
        "age_relaxations": {"value": {}, "confidence": 0.9, "evidence": "per statutory rules"},
        "confidence": 0.9,
    }
    base.update(overrides)
    return json.dumps(base)


@pytest.fixture
async def cleanup_cache():
    yield
    async with AsyncSessionLocal() as db:
        await db.execute(delete(ExtractionCache))
        await db.commit()


async def test_auto_extraction_is_cached(cleanup_cache, monkeypatch):
    calls = {"n": 0}

    async def fake_llm(make_messages):
        calls["n"] += 1
        return _payload()

    monkeypatch.setattr(nx, "_groq_completion", fake_llm)

    pdf = _make_pdf("cache-me " + uuid4().hex)
    first = await nx.extract_notification(pdf)
    assert first.needs_manual_review is False
    assert first.total_vacancies == 150
    assert calls["n"] == 1

    # Second call: served from cache — the LLM must NOT be called again.
    calls["n"] = 0

    async def _boom(make_messages):
        raise AssertionError("LLM must not be consulted on a cache hit")

    async def _no_fallback(messages):
        raise AssertionError("fallback must not be consulted on a cache hit")

    monkeypatch.setattr(nx, "_groq_completion", _boom)
    monkeypatch.setattr(nx, "_fallback_completion", _no_fallback)
    second = await nx.extract_notification(pdf)
    assert second.total_vacancies == 150
    assert second.provider.endswith("cache")
    assert calls["n"] == 0

    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(ExtractionCache))).scalars().all()
        assert [r.status for r in rows] == ["auto"]


async def test_review_verdicts_are_never_cached(cleanup_cache, monkeypatch):
    calls = {"n": 0}

    async def fake_llm(make_messages):
        calls["n"] += 1
        return _payload(**{f: {"value": None, "confidence": 0.1, "evidence": None} for f in nx.CRITICAL_FIELDS})

    async def _no_fallback(messages):
        return None

    monkeypatch.setattr(nx, "_groq_completion", fake_llm)
    monkeypatch.setattr(nx, "_fallback_completion", _no_fallback)

    pdf = _make_pdf("never-cache-me " + uuid4().hex)
    first = await nx.extract_notification(pdf)
    assert first.needs_manual_review is True

    second = await nx.extract_notification(pdf)
    assert second.needs_manual_review is True
    assert calls["n"] == 2

    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(ExtractionCache))).scalars().all()
        assert rows == []


async def test_weak_field_escalates_only_that_field(cleanup_cache, monkeypatch):
    primary = _payload(
        total_vacancies={"value": None, "confidence": 0.2, "evidence": None},
    )

    async def fake_llm(make_messages):
        return primary

    async def fake_fallback(messages):
        # only the escalated field is asked for — assert the prompt asks for it and ONLY it
        content = messages[-1]["content"]
        assert "total_vacancies" in content
        assert "age_max_general" not in content
        return json.dumps(
            {"total_vacancies": {"value": 150, "confidence": 0.95, "evidence": "Total 150 vacancies"}}
        )

    monkeypatch.setattr(nx, "_groq_completion", fake_llm)
    monkeypatch.setattr(nx, "_fallback_completion", fake_fallback)

    pdf = _make_pdf("escalate-me " + uuid4().hex)
    result = await nx.extract_notification(pdf, use_cache=False)
    assert result.total_vacancies == 150
    assert result.field_confidence["total_vacancies"] == 0.95
    assert result.provider == "fallback-merged"
    assert result.needs_manual_review is False


async def test_fallback_not_configured_keeps_review(cleanup_cache, monkeypatch):
    primary = _payload(
        total_vacancies={"value": None, "confidence": 0.2, "evidence": None},
    )

    async def fake_llm(make_messages):
        return primary

    async def _no_fallback(messages):
        return None  # LLM_FALLBACK_* unset → behaves as today

    monkeypatch.setattr(nx, "_groq_completion", fake_llm)
    monkeypatch.setattr(nx, "_fallback_completion", _no_fallback)

    pdf = _make_pdf("keep-review " + uuid4().hex)
    result = await nx.extract_notification(pdf, use_cache=False)
    assert result.needs_manual_review is True
    assert result.total_vacancies is None
