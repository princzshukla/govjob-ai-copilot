"""Discovery engine — offline tests (no network, no DB)."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pymupdf
import pytest

from app.core import admit_cards as ac
from app.services import discovery_engine as de


class FakeResponse:
    def __init__(self, status=200, content=b"", ok=True):
        self.status_code = status
        self.content = content
        self.encoding = "utf-8"
        self.ok = ok


class FakeClient:
    def __init__(self, head_status=200, get_status=200, body=b"", override_get_status=None):
        self.head_status = head_status
        self.get_status = get_status
        self.override_get_status = override_get_status
        self.body = body
        self.calls = []

    async def head(self, url, **kwargs):
        self.calls.append(("HEAD", url))
        return FakeResponse(self.head_status)

    async def get(self, url, **kwargs):
        self.calls.append(("GET", url))
        status = self.override_get_status if self.override_get_status is not None else self.get_status
        return FakeResponse(status, self.body)


def _pdf_bytes(text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((40, 60), text[:300], fontsize=9)
    data = doc.tobytes()
    doc.close()
    return data


def test_analyze_entry_signals():
    a = de.analyze_entry("SSC Junior Engineer JE Admit Card 2026")
    assert a["organization"] == "ssc"
    assert a["recruitment_year"] == "2026"
    assert a["notice_subtype"] == "admit_card"
    b = de.analyze_entry("Notification without a year")
    assert b["recruitment_year"] is None
    assert b["organization"] is None


def test_official_url_validation():
    assert de.is_official_url("https://ssc.gov.in/api/x.pdf", "ssc") is True
    assert de.is_official_url("https://fake.example.com/x.pdf", "ssc") is False
    assert de.is_official_url("https://ssc.gov.in.evil.com/x.pdf", "ssc") is False
    assert de.is_official_url("https://example.com/x.pdf", None) is False


async def test_official_pdf_verification():
    body = _pdf_bytes("SSC Junior Engineer JE Admit Card 2026 exam city intimation")
    client = FakeClient(head_status=200, body=body)
    result = await de.verify_official_candidate(
        "https://ssc.gov.in/api/attachment/x.pdf", "SSC Junior Engineer JE Admit Card 2026", client
    )
    assert result["reachable"] is True
    assert result["is_pdf"] is True
    assert result["document_matched"] is True
    assert result["token_overlap"] >= 0.4


async def test_invalid_official_url_is_not_verified():
    client = FakeClient(head_status=404, override_get_status=404)
    result = await de.verify_official_candidate(
        "https://fake.example.com/x.pdf", "SSC JE Admit Card 2026", client
    )
    assert result["reachable"] is False
    assert result["document_matched"] is False
    assert result["reason"] == "http_404"


def test_duplicate_detection_variants():
    existing = [
        {"id": "seed-1", "url": "https://ssc.gov.in/a.pdf", "title": "SSC JE Admit Card 2026",
         "organization": "ssc", "year": "2026"},
        {"id": "db-1", "url": None, "title": "UPSC IFS Main Admit Card 2026",
         "organization": "upsc", "year": "2026"},
    ]
    assert de.detect_duplicate(
        analysis=de.analyze_entry("SSC JE Admit Card 2026"),
        official_url="https://ssc.gov.in/a.pdf", existing=existing,
    )["reason"] == "exact_url"
    assert de.detect_duplicate(
        analysis=de.analyze_entry("another title"), official_url=None,
        existing=[{"id": "q1", "title": "Another Title", "url": None}],
    )["reason"] == "normalized_title"
    assert de.detect_duplicate(
        analysis=de.analyze_entry("SSC JE Admit Card 2026 — exam city"),
        official_url=None, existing=existing,
    )["reason"] == "same_org_year_same_notice"


def test_incorrect_organization_is_not_a_duplicate():
    existing = [{"id": "seed-1", "url": None, "title": "SBI Clerk Mains Admit Card 2026",
                 "organization": "sbi", "year": "2026"}]
    result = de.detect_duplicate(
        analysis=de.analyze_entry("UPESSC Assistant Professor Admit Card 2026"),
        official_url=None, existing=existing,
    )
    assert result["is_duplicate"] is False


def test_missing_dates_are_not_invented():
    a = de.analyze_entry("Some Board Admit Card — date to be announced")
    assert a["recruitment_year"] is None
    assert de.compute_confidence(a, None, None) < 0.7


def test_approval_gate_requires_official_evidence():
    rec = SimpleNamespace(
        discovery_status=de.STATUS_PDF_VERIFIED,
        verification_status="official_evidence",
        official_pdf_url="https://ssc.gov.in/x.pdf",
        official_notification_url=None,
    )
    assert de.validate_approval(rec) is None
    rec.verification_status = "official_source_only"
    assert de.validate_approval(rec) == "no_verified_official_evidence"
    rec.official_pdf_url = None
    assert de.validate_approval(rec) == "no_official_url"
    rec.discovery_status = de.STATUS_REJECTED
    assert de.validate_approval(rec).startswith("invalid status")


def test_idempotent_seed_insertion(monkeypatch, tmp_path):
    overlay = tmp_path / "approved.json"
    monkeypatch.setattr(ac, "APPROVED_SEED_PATH", overlay)
    monkeypatch.setattr(ac, "SEED_ADMIT_CARDS", list(ac.SEED_ADMIT_CARDS))
    item = {
        "id": "disc-1", "title": "Test Board Admit Card 2026", "organizing_body": "TEST",
        "exam_name": None, "link_kind": "notice_pdf", "notice_subtype": "admit_card",
        "notification_date": None, "exam_date": None,
        "admit_url": "https://example.gov.in/x.pdf", "source_url": "https://example.gov.in/x.pdf",
    }
    assert ac.record_approved_seed(item)["id"] == "disc-1"
    with pytest.raises(ValueError):
        ac.record_approved_seed(item)
    assert len(json.loads(overlay.read_text(encoding="utf-8"))) == 1
    assert len(ac.SEED_ADMIT_CARDS) == 41  # base list + one overlay row
