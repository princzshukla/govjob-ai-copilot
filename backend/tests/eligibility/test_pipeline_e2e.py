"""Step 4 — end-to-end eligibility: resume upload → manual completion → verdicts.

Three deliberately tricky profiles, asserting exact verdicts (this file is a
regression suite for "never show a wrong eligibility result"):

* **Boundary** — exactly 30 on the cutoff for a 30-year exam (eligible), then
  one year older (ineligible for UR, eligible for OBC-NCL via +3).
* **Final Year / Appearing** — an exam whose final-year policy is unstated
  must land in check_manually, never in "eligible"; an explicit allow →
  eligible, an explicit deny → ineligible.
* **Reserved category** — OBC-NCL relaxation (+3) unlocks a 30-year limit
  exam at age 31; the same candidate as General does not clear it.

The resume-upload path is exercised the same way the frontend uses it:
parse (mocked LLM) → user completes DOB/category → profile is saved →
GET /eligibility.
"""
from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import delete

from app.api.v1.endpoints import candidate as candidate_module
from app.core.database import AsyncSessionLocal
from app.models.exam import ExamNotification
from app.schemas.candidate import ParsedResumeProfile

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
PARSE_RESUME_URL = "/api/v1/candidate/parse-resume"
PROFILE_URL = "/api/v1/candidate/profile"
PASSWORD = "correct-horse-battery"

DOB_BOUNDARY = date(1996, 3, 15)   # exactly 30 on the 2026-08-01 cutoff
DOB_OVER_BOUNDARY = date(1995, 3, 15)  # 31 on that cutoff

async def _register_and_login(client, email: str) -> None:
    resp = await client.post(REGISTER_URL, json={"email": email, "password": PASSWORD, "full_name": "E2E User"})
    assert resp.status_code == 201, resp.text
    resp = await client.post(LOGIN_URL, json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200, resp.text

def _profile_payload(**overrides) -> dict:
    payload = {
        "full_name": "E2E Candidate",
        "dob": DOB_BOUNDARY.isoformat(),
        "gender": "Male",
        "category": "General",
        "is_pwd": False,
        "domicile_state": "Uttar Pradesh",
        "highest_degree": "B.Tech",
        "stream": "Computer Science",
        "percentage_cgpa": 72.0,
        "passing_year": 2018,
        "graduation_status": "Completed",
        "previous_attempts": 0,
    }
    payload.update(overrides)
    return payload

async def _save_profile(client, **overrides) -> str:
    resp = await client.post(PROFILE_URL, json=_profile_payload(**overrides))
    assert resp.status_code == 201, resp.text
    return resp.json()["profile_id"]

async def _eligibility(client, profile_id: str) -> dict:
    resp = await client.get(f"/api/v1/candidate/profile/{profile_id}/eligibility")
    assert resp.status_code == 200, resp.text
    return resp.json()

def _by_exam(payload: dict, bucket: str) -> dict[str, dict]:
    return {exam["exam_id"]: exam for exam in payload[bucket]}

# ---------------------------------------------------------------------------
# Profile 1 — resume upload, then manual DOB/category completion (age boundary)
# ---------------------------------------------------------------------------

async def test_resume_upload_manual_completion_boundary(client, monkeypatch):
    async def fake_parse(_raw_text: str):
        # What the LLM honestly returns for a resume with no DOB/category,
        # plus the endpoint's real missing-field inspection on top.
        from app.services.parser import inspect_missing_gov_fields
        from app.schemas.candidate import ResumeParseResponse

        profile = ParsedResumeProfile(
            full_name="Resume Candidate",
            highest_degree="B.Tech",
            stream="Computer Science",
            percentage_cgpa=70.0,
            passing_year=2018,
            graduation_status="Completed",
            dob=None,
            category=None,
        )
        missing = inspect_missing_gov_fields(profile)
        return ResumeParseResponse(
            extracted_profile=profile,
            is_complete_for_gov_jobs=False,
            missing_fields=missing,
            message="Please complete the highlighted details.",
        )

    monkeypatch.setattr(candidate_module, "extract_raw_text_from_pdf", lambda _b: "fake resume text")
    monkeypatch.setattr(candidate_module, "parse_resume_with_groq", fake_parse)

    email = f"e2e-resume-{uuid4().hex[:8]}@example.com"
    await _register_and_login(client, email)

    resp = await client.post(
        PARSE_RESUME_URL,
        files={"file": ("resume.pdf", b"%PDF-1.4 fake-resume-bytes", "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    missing = {field["field_name"] for field in body["missing_fields"]}
    assert {"dob", "category"} <= missing

    # Manual completion: boundary age (exactly 30 at the cutoff).
    profile_id = await _save_profile(client, dob=DOB_BOUNDARY.isoformat(), category="General")
    eligibility = await _eligibility(client, profile_id)
    eligible_now = _by_exam(eligibility, "eligible_now")
    assert "ssc-cgl-general" in eligible_now          # age == 30, exact boundary is in
    assert "sbi-po-general" in eligible_now           # 30-year limit: in
    assert "rrb-ntpc-grad" in eligible_now
    assert "ib-acio-grade-ii" not in eligible_now     # 27-year limit: too old

    # One year older → role reversal on the 30-year exams.
    profile_id = await _save_profile(
        client, dob=DOB_OVER_BOUNDARY.isoformat(), category="General"
    )
    eligibility = await _eligibility(client, profile_id)
    eligible_now = _by_exam(eligibility, "eligible_now")
    ineligible = _by_exam(eligibility, "ineligible")
    assert "ssc-cgl-general" not in eligible_now
    assert "ssc-cgl-general" in ineligible
    assert "rrb-ntpc-grad" in eligible_now            # 33-year limit still clears

# ---------------------------------------------------------------------------
# Profile 2 — OBC-NCL relaxation unlocks a 30-year exam at 31
# ---------------------------------------------------------------------------

async def test_obc_ncl_relaxation_boundary(client):
    email = f"e2e-obc-{uuid4().hex[:8]}@example.com"
    await _register_and_login(client, email)

    profile_id = await _save_profile(
        client,
        dob=DOB_OVER_BOUNDARY.isoformat(),  # 31 on the CGL cutoff
        category="OBC-NCL",
        highest_degree="B.Com",
        stream="Commerce",
        percentage_cgpa=68.0,
        passing_year=2016,
    )
    eligibility = await _eligibility(client, profile_id)
    eligible_now = _by_exam(eligibility, "eligible_now")
    assert "ssc-cgl-general" in eligible_now          # 31 ≤ 30 + 3 (OBC-NCL)
    assert "sbi-po-general" in eligible_now           # 31 ≤ 30 + 3
    assert "ib-acio-grade-ii" not in eligible_now     # 31 > 27 + 3

    # Same candidate, General category → the 30-year exams close.
    profile_id = await _save_profile(
        client,
        dob=DOB_OVER_BOUNDARY.isoformat(),
        category="General",
        highest_degree="B.Com",
        stream="Commerce",
        percentage_cgpa=68.0,
        passing_year=2016,
    )
    eligibility = await _eligibility(client, profile_id)
    eligible_now = _by_exam(eligibility, "eligible_now")
    ineligible = _by_exam(eligibility, "ineligible")
    assert "ssc-cgl-general" not in eligible_now
    assert "ssc-cgl-general" in ineligible
    assert "sbi-po-general" in ineligible

# ---------------------------------------------------------------------------
# Profile 3 — Final Year / Appearing must never read as "eligible" by default
# ---------------------------------------------------------------------------

async def test_final_year_appearing_policy(client):
    fyt_yes = ExamNotification(
        id=f"test-fyt-allowed-{uuid4().hex[:8]}",
        title="Final Year OK Exam (test)",
        organizing_body="Test Commission",
        post_type="General Graduate",
        application_deadline=date(2026, 12, 31),
        min_age=18,
        max_age_general=35,
        age_cutoff_date=date(2026, 11, 1),
        allowed_degrees=["Any Graduate"],
        allowed_streams=["Any"],
        min_percentage=0.0,
        allows_final_year=True,
        topics=["Test"],
        source_url="https://example.gov.in/test-fyt-allowed",
        is_active=True,
    )
    fyt_no = ExamNotification(
        id=f"test-fyt-denied-{uuid4().hex[:8]}",
        title="Final Year NO Exam (test)",
        organizing_body="Test Commission",
        post_type="General Graduate",
        application_deadline=date(2026, 12, 31),
        min_age=18,
        max_age_general=35,
        age_cutoff_date=date(2026, 11, 1),
        allowed_degrees=["Any Graduate"],
        allowed_streams=["Any"],
        min_percentage=0.0,
        allows_final_year=False,
        topics=["Test"],
        source_url="https://example.gov.in/test-fyt-denied",
        is_active=True,
    )
    async with AsyncSessionLocal() as db:
        db.add_all([fyt_yes, fyt_no])
        await db.commit()

    try:
        email = f"e2e-fyt-{uuid4().hex[:8]}@example.com"
        await _register_and_login(client, email)

        profile_id = await _save_profile(
            client,
            dob=date(2003, 1, 1).isoformat(),  # 23 at the synthetic cutoffs
            graduation_status="Final Year / Appearing",
        )
        eligibility = await _eligibility(client, profile_id)
        eligible_now = _by_exam(eligibility, "eligible_now")
        check_manually = _by_exam(eligibility, "check_manually")
        ineligible = _by_exam(eligibility, "ineligible")

        # Final-year policy explicitly allowed → eligible.
        assert fyt_yes.id in eligible_now
        # Policy explicitly denied → ineligible.
        assert fyt_no.id in ineligible
        # Seed exams (policy unstated) → check_manually, NEVER "eligible".
        assert "ssc-cgl-general" not in eligible_now
        assert "ssc-cgl-general" in check_manually
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(ExamNotification).where(ExamNotification.id.in_([fyt_yes.id, fyt_no.id])))
            await db.commit()
