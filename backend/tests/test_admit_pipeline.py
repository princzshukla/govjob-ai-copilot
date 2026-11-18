"""Admit-card pipeline — offline unit tests (no DB, no network, no LLM)."""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.services.admit_extractor import _parse_llm_payload, _validate_and_flag
from app.services.admit_publisher import build_admit_card
from app.services.layer2_worker import detect_notice_kind


def _link(title=None, url="https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/n.pdf", published_at=None):
    return SimpleNamespace(title=title, url=url, published_at=published_at)


def _source(config=None):
    return SimpleNamespace(config=config or {}, name="SSC — Notice Board")


def test_detect_notice_kind_ssc_headlines():
    src = _source()
    admit = _link("Information regarding city of examination and Admit Card for the candidates of CGEPT-01/27")
    city = _link("Information regarding the city of examination and admission certificate for candidates")
    job = _link("SSC CGL Tier-I Answer Key 2026 – Out")
    assert detect_notice_kind(admit, src) == "admit_card"
    assert detect_notice_kind(city, src) == "admit_card"
    assert detect_notice_kind(job, src) == "job"


def test_detect_notice_kind_forced_by_source_config():
    src = _source({"notice_kind": "admit_card"})
    job_headline = _link("SSC CGL Tier-I Answer Key 2026")
    assert detect_notice_kind(job_headline, src) == "admit_card"


def test_parse_llm_payload_envelope_and_scores():
    parsed = {
        "exam_name": {"value": "CGEPT 01/2027 (Indian Coast Guard)", "confidence": 0.9, "evidence": "CGEPT 01/2027"},
        "exam_date": {"value": "2027-02-18", "confidence": 0.8, "evidence": "18 February 2027"},
        "notification_date": {"value": "2026-11-06", "confidence": 0.7, "evidence": "06-11-2026"},
        "confidence": 0.8,
    }
    extraction, err = _parse_llm_payload(parsed)
    assert err is None
    assert extraction.exam_name == "CGEPT 01/2027 (Indian Coast Guard)"
    assert extraction.exam_date == date(2027, 2, 18)
    assert extraction.confidence == 0.7  # min of the field confidences


def test_parse_llm_payload_flags_missing_exam_name():
    extraction, err = _parse_llm_payload({"exam_date": {"value": "2027-02-18", "confidence": 0.9}})
    assert err is None
    result = _validate_and_flag(extraction, raw_chars=100, is_scanned=False, provider="groq", headline=None)
    assert result.needs_manual_review is True
    assert any("exam_name" in r for r in result.review_reasons)


def test_validate_and_flag_headline_rescues_exam_name():
    extraction, _ = _parse_llm_payload({"exam_name": {"value": None, "confidence": 0.1}})
    result = _validate_and_flag(
        extraction,
        raw_chars=100,
        is_scanned=False,
        provider="groq",
        headline="City of examination and Admit Card CGEPT-01/27",
    )
    # headline rescues the name only via the caller (extract_admit_card sets it);
    # here the validator sees exam_name still missing but a headline exists, so
    # no "exam_name missing" reason is added — low confidence still flags review.
    assert all("exam_name missing" not in r for r in result.review_reasons)


def test_build_admit_card_uses_headline_and_link():
    extraction = SimpleNamespace(
        id=42,
        extracted={"kind": "admit_card", "exam_name": "CGEPT 01/2027", "exam_date": "2027-02-18", "notification_date": None},
    )
    link = _link("SSC — CGEPT 01/2027 Admit Card", published_at=None)
    card, problems = build_admit_card(extraction, link, _source())
    assert problems == []
    assert card.id == "admit-ext-42"
    assert card.admit_url == link.url
    assert card.title == "SSC — CGEPT 01/2027 Admit Card"
    assert card.exam_date == date(2027, 2, 18)
    assert card.organizing_body == "SSC — Notice Board"


def test_build_admit_card_holds_when_nothing_identifiable():
    extraction = SimpleNamespace(id=7, extracted={"kind": "admit_card", "exam_name": None, "exam_date": None})
    link = _link(None)
    card, problems = build_admit_card(extraction, link, _source())
    assert card is None
    assert any("exam_name" in p for p in problems)


def test_validate_and_flag_holds_past_exam_date():
    from app.services.admit_extractor import _validate_and_flag, _parse_llm_payload
    from datetime import date

    parsed = {
        "exam_name": {"value": "Some Exam 2026: Admit Card", "confidence": 0.9, "evidence": "admit card"},
        "exam_date": {"value": "2020-05-01", "confidence": 0.9, "evidence": "1 May 2020"},
    }
    extraction, err = _parse_llm_payload(parsed)
    assert err is None
    result = _validate_and_flag(extraction, raw_chars=100, is_scanned=False, provider="groq", headline="Some Exam")
    assert result.needs_manual_review is True
    assert any("past" in r for r in result.review_reasons)


def test_validate_and_flag_holds_reversed_dates():
    from app.services.admit_extractor import _validate_and_flag, _parse_llm_payload

    parsed = {
        "exam_name": {"value": "Some Exam 2027: Admit Card", "confidence": 0.95, "evidence": "admit card"},
        "exam_date": {"value": "2027-01-01", "confidence": 0.95, "evidence": "1 Jan 2027"},
        "notification_date": {"value": "2027-06-01", "confidence": 0.95, "evidence": "1 Jun 2027"},
    }
    extraction, err = _parse_llm_payload(parsed)
    assert err is None
    result = _validate_and_flag(extraction, raw_chars=100, is_scanned=False, provider="groq", headline="Some Exam")
    assert result.needs_manual_review is True


def test_validate_and_flag_accepts_sane_card():
    from app.services.admit_extractor import _validate_and_flag, _parse_llm_payload

    parsed = {
        "exam_name": {"value": "RRB NTPC 2026: Admit Card", "confidence": 0.9, "evidence": "admit card"},
        "exam_date": {"value": "2027-03-01", "confidence": 0.9, "evidence": "1 Mar 2027"},
        "notification_date": {"value": "2026-11-10", "confidence": 0.9, "evidence": "10 Nov 2026"},
    }
    extraction, err = _parse_llm_payload(parsed)
    assert err is None
    result = _validate_and_flag(extraction, raw_chars=100, is_scanned=False, provider="groq", headline="RRB NTPC")
    # 2026-11-10 <= exam_date 2027-03-01 and both plausible → clean auto
    assert result.needs_manual_review is False
