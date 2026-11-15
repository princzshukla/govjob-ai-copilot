"""Table-driven matcher tests for the tricky statutory rules.

Complements the JSON golden set with sharp, human-readable rule matrices:
age-on-cutoff boundaries (UR/OBC/SC/ST/PwBD/EWS), Any-Graduate semantics,
final-year ("Appearing") tri-state, DOB-after-cutoff, min-age boundary, and
max-attempts. One row = one case; ids are stable for failure triage.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.models.exam import ExamNotification
from app.schemas.candidate import CandidateProfileCreate
from app.services.matcher import check_single_exam_eligibility

EXAM_KW = dict(
    id="matcher-golden",
    title="Matcher Golden Notification",
    organizing_body="Golden Test Commission",
    post_type="General",
    application_deadline=date(2026, 12, 31),
    official_pdf_url="https://example.gov.in/notification.pdf",
    min_age=18,
    max_age_general=30,
    age_cutoff_date=date(2026, 8, 1),
    allowed_degrees=["Any Graduate"],
    allowed_streams=["Any"],
    min_percentage=0.0,
    is_active=True,
    topics=["General Intelligence"],
)

BASE_CAND = dict(
    full_name="Matcher Golden",
    dob=date(2000, 1, 1),
    gender="Male",
    category="General",
    is_pwd=False,
    domicile_state="Maharashtra",
    highest_degree="B.Tech",
    stream="Computer Science",
    percentage_cgpa=75.0,
    passing_year=2022,
    graduation_status="Completed",
    previous_attempts=0,
)

CASES = [
    # --- Age on the cutoff date (max 30 on 2026-08-01) ---
    dict(id="age_exactly_at_general_limit", overrides={}, verdict="eligible"),
    dict(id="age_31_general_fails", overrides={"dob": date(1995, 3, 15)}, verdict="ineligible"),
    dict(id="age_obc_plus3_at_33", overrides={"dob": date(1995, 3, 15), "category": "OBC"}, verdict="eligible"),
    dict(id="age_obc_ncl_plus3_alias", overrides={"dob": date(1995, 3, 15), "category": "OBC-NCL"}, verdict="eligible"),
    dict(id="age_obc_plus3_fails_at_34", overrides={"dob": date(1992, 3, 15), "category": "OBC"}, verdict="ineligible"),
    dict(id="age_sc_plus5_at_35", overrides={"dob": date(1993, 3, 15), "category": "SC"}, verdict="eligible"),
    dict(id="age_st_plus5_at_35", overrides={"dob": date(1993, 3, 15), "category": "ST"}, verdict="eligible"),
    dict(id="age_sc_plus5_fails_at_36", overrides={"dob": date(1990, 3, 15), "category": "SC"}, verdict="ineligible"),
    dict(id="age_pwd_plus10_at_40", overrides={"dob": date(1988, 3, 15), "is_pwd": True}, verdict="eligible"),
    dict(id="age_obc_pwd_plus13_at_43", overrides={"dob": date(1985, 3, 15), "category": "OBC", "is_pwd": True}, verdict="eligible"),
    dict(id="age_sc_pwd_plus15_at_45", overrides={"dob": date(1983, 3, 15), "category": "SC", "is_pwd": True}, verdict="eligible"),
    dict(id="age_pwd_plus10_fails_at_41", overrides={"dob": date(1985, 3, 15), "is_pwd": True}, verdict="ineligible"),
    # --- Any Graduate semantics ---
    dict(id="bsc_any_graduate_ok", overrides={"highest_degree": "B.Sc"}, verdict="eligible"),
    dict(id="bca_any_graduate_ok", overrides={"highest_degree": "BCA"}, verdict="eligible"),
    dict(id="mtech_beats_any_graduate", overrides={"highest_degree": "M.Tech"}, verdict="eligible"),
    dict(id="diploma_fails_any_graduate", overrides={"highest_degree": "Diploma"}, verdict="ineligible"),
    dict(id="12th_fails_any_graduate", overrides={"highest_degree": "12th"}, verdict="ineligible"),
    dict(id="unrecognized_degree_needs_check", overrides={"highest_degree": "Advanced Certificate in Dental Radiology"}, verdict="check_manually"),
    # --- Final year / appearing tri-state ---
    dict(id="final_year_unstated_policy_check_manually", overrides={"graduation_status": "Final Year / Appearing"}, verdict="check_manually"),
    dict(id="final_year_allowed_eligible", overrides={"graduation_status": "Final Year / Appearing"}, exam_overrides={"allows_final_year": True}, verdict="eligible"),
    dict(id="final_year_not_allowed_ineligible", overrides={"graduation_status": "Final Year / Appearing"}, exam_overrides={"allows_final_year": False}, verdict="ineligible"),
    # --- Cutoff edge cases ---
    dict(id="dob_after_cutoff_cannot_verify", overrides={"dob": date(2026, 9, 1)}, verdict="check_manually"),
    dict(id="underage_ineligible_at_18_boundary", overrides={"dob": date(2009, 8, 2)}, verdict="ineligible"),
    dict(id="exactly_18_on_cutoff_eligible", overrides={"dob": date(2008, 8, 1)}, verdict="eligible"),
    # --- Max attempts ---
    dict(id="max_attempts_at_limit_ok", overrides={"previous_attempts": 2}, exam_overrides={"max_attempts": 3}, verdict="eligible"),
    dict(id="max_attempts_over_limit", overrides={"previous_attempts": 3}, exam_overrides={"max_attempts": 3}, verdict="ineligible"),
]


def _candidate(overrides: dict) -> CandidateProfileCreate:
    return CandidateProfileCreate(**{**BASE_CAND, **overrides})


def _exam(exam_overrides: dict) -> ExamNotification:
    return ExamNotification(**{**EXAM_KW, **exam_overrides})


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_matcher_rule(case):
    cand = _candidate(case.get("overrides", {}))
    exam = _exam(case.get("exam_overrides", {}))
    result = check_single_exam_eligibility(cand, exam, exam_topics_map={})
    assert result.verdict == case["verdict"], (
        f"{case['id']}: expected {case['verdict']}, got {result.verdict}. "
        + " | ".join(f"{r.rule}={r.status}({r.message})" for r in result.rules if r.status != "passed")
    )


def test_unknown_category_is_needs_check_not_silent_zero():
    cand = _candidate({"category": "Brahmin"})
    exam = _exam({})
    result = check_single_exam_eligibility(cand, exam, exam_topics_map={})
    category_rule = next(r for r in result.rules if r.rule == "Category relaxation")
    assert category_rule.status == "needs_check"
