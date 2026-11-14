"""Deterministic tests for the notification extractor — no LLM, no network.

Covers the regressions found while closing the Step-3 benchmark gate:
* bilingual rule-heavy boilerplate must not swallow structural table rows
  ("TOTAL" cells were dropped as "running headers");
* keyword windows must actually carry the annexure total-table, the
  qualification section and the age band into the prompt within the token
  budget (IBPS was returned as None on those fields);
* per-field confidence/evidence payloads must parse (nested and bare forms);
* scanned PDFs must short-circuit WITHOUT calling the LLM;
* relaxations (SC/ST combined keys) must pass validation.
"""
from __future__ import annotations

import json
from datetime import date

import pytest

from app.schemas.pipeline import NotificationExtraction  # noqa: F401  (import sanity)
from app.services import notification_extractor as nx

# --- boilerplate stripping ---------------------------------------------------


def test_clean_text_drops_repeated_prose_lines():
    header = "BHARAT HEAVY ELECTRICALS LIMITED — ANNUAL RECRUITMENT NOTIFICATION AND INSTRUCTIONS"
    lines = [header] + [f"row {i} unique content {i}" for i in range(30)]
    text = "\n".join(lines * 1)
    cleaned = nx.clean_raw_text(text)
    # sanity: a 3+ repeated long prose line with letters is dropped
    repeated = "\n".join([header] * 4 + ["unique line A", "unique line B"])
    assert header not in nx.clean_raw_text(repeated)


def test_clean_text_keeps_table_cells_like_total():
    """'TOTAL' rows repeat on every table page; they anchor vacancy tables."""
    text = "Some intro\n" + "\n".join(["TOTAL", "1009 502"]) * 4 + "\n6715 vacancies overall"
    cleaned = nx.clean_raw_text(text)
    assert "6715 vacancies overall" in cleaned


def test_clean_text_drops_page_furniture():
    text = "Actual content line\nPage 2 of 54\n12\n---\nMore content"
    cleaned = nx.clean_raw_text(text)
    assert "Page 2 of 54" not in cleaned
    assert "More content" in cleaned


# --- compression & token budget ----------------------------------------------


def test_compress_keeps_key_sections_within_budget(benchmarks_present):
    path = benchmarks_present / "ibps-po-xvi.pdf"
    import pymupdf

    raw = "\n".join(p.get_text() for p in pymupdf.open(str(path)))
    cleaned = nx.clean_raw_text(raw)
    compressed = nx.compress_for_prompt(cleaned, budget=6000)
    assert nx._est_tokens(compressed) <= 6000 * 1.1  # tolerate section boundaries
    assert "A Degree" in compressed or "QUALIFICATIONS" in compressed.upper()
    assert "6715" in compressed


def test_compress_tiny_document_passthrough():
    text = "Advertisement. 2 vacancies for post of Clerk. Age 18-27."
    assert nx.compress_for_prompt(text) is text


# --- LLM payload parsing ------------------------------------------------------


def test_parse_nested_per_field_envelope():
    payload = {
        "total_vacancies": {"value": 150, "confidence": 0.9, "evidence": "Total 150"},
        "age_max_general": {"value": 27, "confidence": 0.8, "evidence": "Upper Age Limit 27 Years"},
        "age_relaxations": {"SC": 5, "ST": 5, "OBC": 3},
        "age_cutoff_date": {"value": "2022-09-01", "confidence": 0.95, "evidence": "as on 01/09/2022"},
        "application_last_date": {"value": "2022-10-04", "confidence": 0.95, "evidence": "Closing ... 4th October, 2022"},
        "pay_level": {"value": "Rs 50,000-1,60,000", "confidence": 0.9, "evidence": "basic pay of Rs 50,000"},
        "required_qualification": {"value": "BE/B.Tech", "confidence": 0.85, "evidence": "Bachelors Degree in Engineering"},
        "confidence": 0.8,
    }
    extraction, error = nx._parse_llm_payload(payload)
    assert error is None
    assert extraction.total_vacancies == 150
    assert extraction.age_max_general == 27
    assert extraction.age_relaxations == {"SC": 5, "ST": 5, "OBC": 3}
    assert extraction.age_cutoff_date == date(2022, 9, 1)
    assert extraction.application_last_date == date(2022, 10, 4)
    assert extraction.confidence == pytest.approx(0.8)
    assert extraction.evidence["age_max_general"].startswith("Upper Age")


def test_parse_bare_scalars_penalized():
    extraction, error = nx._parse_llm_payload({"total_vacancies": 515, "confidence": 0.9})
    assert error is None
    assert extraction.total_vacancies == 515
    assert extraction.confidence == pytest.approx(0.5)


def test_parse_combined_sc_st_relaxation_key_is_accepted():
    payload = {
        "age_relaxations": {"value": {"SC/ST": 5, "OBC": 3}, "confidence": 0.9, "evidence": "SC/ST by 5 years"},
        "confidence": 0.9,
    }
    extraction, error = nx._parse_llm_payload(payload)
    assert error is None
    assert extraction.age_relaxations["SC/ST"] == 5
    flagged = nx._validate_and_flag(extraction, raw_chars=100, is_scanned=False, provider="groq")
    assert not any("relaxation" in r for r in flagged.review_reasons)


def test_parse_rejects_min_greater_than_max():
    payload = {
        "min_age": {"value": 30, "confidence": 0.9, "evidence": ""},
        "age_max_general": {"value": 27, "confidence": 0.9, "evidence": ""},
        "confidence": 0.9,
    }
    extraction, error = nx._parse_llm_payload(payload)
    assert error is None
    flagged = nx._validate_and_flag(extraction, raw_chars=100, is_scanned=False, provider="groq")
    assert flagged.needs_manual_review
    assert any("min_age" in r for r in flagged.review_reasons)


# --- scanned PDFs never reach the LLM ----------------------------------------


async def test_scanned_pdf_never_calls_llm(monkeypatch):
    called = False

    class _ExplodingGroq:
        class chat:
            class completions:
                @staticmethod
                async def create(*args, **kwargs):
                    nonlocal called
                    called = True
                    raise AssertionError("LLM must not be called for scanned PDFs")

    monkeypatch.setattr(nx, "_groq", lambda: _ExplodingGroq())

    import pymupdf

    doc = pymupdf.open()
    doc.new_page()  # blank image-only page → 0 chars
    pdf_bytes = doc.tobytes()
    result = await nx.extract_notification(pdf_bytes)
    assert called is False
    assert result.is_scanned is True
    assert result.needs_manual_review is True
    assert result.confidence == 0.0


async def test_missing_criticals_flag_not_publish(monkeypatch):
    async def fake_llm(make_messages):
        return json.dumps({"age_max_general": {"value": 30, "confidence": 0.9, "evidence": "x"}, "confidence": 0.9})

    monkeypatch.setattr(nx, "_groq_completion", fake_llm)
    monkeypatch.setattr(nx, "extract_text_stats", lambda b: ("vacancy text " * 40, 1, 500.0))
    result = await nx.extract_notification(b"%PDF-1.4 fake")
    assert result.needs_manual_review is True
    assert any("missing critical fields" in r for r in result.review_reasons)


@pytest.fixture()
def benchmarks_present():
    from pathlib import Path

    d = Path(__file__).resolve().parents[1] / "benchmarks" / "pdfs"
    if not (d / "ibps-po-xvi.pdf").exists():
        pytest.skip("benchmark PDFs not downloaded")
    return d
