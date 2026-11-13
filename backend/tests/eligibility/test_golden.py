import json
from datetime import date
from pathlib import Path

import pytest

from app.models.exam import ExamNotification
from app.schemas.candidate import CandidateProfileCreate
from app.services.matcher import check_single_exam_eligibility, evaluate_all_exams

GOLDEN_DIR = Path(__file__).parent / "golden"
GOLDEN_PATH = GOLDEN_DIR / "golden_cases.json"
GOLDEN_DATA = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
DEFAULTS = GOLDEN_DATA["defaults"]
CASES = GOLDEN_DATA["cases"]

DATE_FIELDS = (
    "notification_date",
    "application_deadline",
    "exam_date",
    "age_cutoff_date",
    "last_checked_at",
)
VALID_VERDICTS = {"eligible", "check_manually", "ineligible"}
VALID_RULE_STATUSES = {"passed", "failed", "needs_check"}


def _make_exam(overrides: dict) -> ExamNotification:
    raw = {**DEFAULTS["exam"], **overrides}
    for field in DATE_FIELDS:
        if raw.get(field):
            raw[field] = date.fromisoformat(raw[field])
    return ExamNotification(**raw)


def _make_candidate(overrides: dict) -> CandidateProfileCreate:
    return CandidateProfileCreate(**{**DEFAULTS["candidate"], **overrides})


def _run_case(case: dict):
    candidate = _make_candidate(case.get("candidate", {}))
    exam = _make_exam(case.get("exam", {}))
    return check_single_exam_eligibility(candidate, exam, exam_topics_map={})


def test_golden_set_has_at_least_50_cases():
    assert len(CASES) >= 50


def test_golden_case_ids_are_unique():
    ids = [case["id"] for case in CASES]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_golden_case(case):
    result = _run_case(case)

    assert result.verdict == case["expected_verdict"], (
        f"{case['id']}: expected {case['expected_verdict']}, got {result.verdict}. "
        f"Rules: {[(r.rule, r.status, r.message) for r in result.rules]}"
    )

    if "expected_failed_rules" in case:
        actual = [rule.rule for rule in result.rules if rule.status == "failed"]
        assert actual == case["expected_failed_rules"], (
            f"{case['id']}: failed rules were {actual}"
        )

    if "expected_needs_check_rules" in case:
        actual = [rule.rule for rule in result.rules if rule.status == "needs_check"]
        assert actual == case["expected_needs_check_rules"], (
            f"{case['id']}: needs-check rules were {actual}"
        )

    if "expected_last_attempt" in case:
        assert result.is_last_attempt_age is case["expected_last_attempt"]


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_every_result_has_rule_explanations_and_source(case):
    result = _run_case(case)

    assert result.verdict in VALID_VERDICTS
    assert result.is_eligible is (result.verdict == "eligible")
    assert result.check_manually is (result.verdict == "check_manually")
    assert bool(result.reasons_failed) is (result.verdict == "ineligible")

    assert result.source_url, f"{case['id']}: missing source_url"
    assert result.last_checked_at, f"{case['id']}: missing last_checked_at"
    assert result.rules, f"{case['id']}: no rule explanations"

    rule_names = {rule.rule for rule in result.rules}
    assert {"Age on cutoff date", "Educational qualification"} <= rule_names

    for rule in result.rules:
        assert rule.status in VALID_RULE_STATUSES
        assert rule.rule.strip()
        assert rule.candidate_value.strip()
        assert rule.required_value.strip()
        assert rule.message.strip()


def test_verify_cases_are_explicitly_marked():
    """Cases needing confirmation against a real notification are flagged in JSON."""
    verify_ids = [case["id"] for case in CASES if case.get("verify")]
    assert verify_ids, "at least one golden case should be marked verify: true"


def test_evaluate_all_exams_returns_three_verdict_buckets():
    candidate = _make_candidate(
        {"highest_degree": "B.Com", "graduation_status": "Final Year / Appearing"}
    )
    exams = [
        _make_exam({"id": "golden-eligible", "allows_final_year": True}),
        _make_exam(
            {
                "id": "golden-ineligible",
                "allowed_degrees": ["B.Tech"],
                "allows_final_year": True,
            }
        ),
        _make_exam(
            {
                "id": "golden-manual",
                "allowed_degrees": ["Any Graduate"],
                "allows_final_year": None,
            }
        ),
    ]

    response = evaluate_all_exams(candidate, exams, exam_topics_map={})

    assert [item.exam_id for item in response.eligible_now] == ["golden-eligible"]
    assert [item.exam_id for item in response.ineligible] == ["golden-ineligible"]
    assert [item.exam_id for item in response.check_manually] == ["golden-manual"]
