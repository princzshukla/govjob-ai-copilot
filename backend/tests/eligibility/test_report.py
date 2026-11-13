from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.report import EligibilityReport

REPORT_URL = "/api/v1/eligibility/report"
CHECK_URL = "/api/v1/eligibility/check"
EXAMS_URL = "/api/v1/eligibility/exams"

CANDIDATE = {
    "full_name": "Private Person",
    "dob": "1999-05-20",
    "gender": "Male",
    "category": "OBC-NCL",
    "is_pwd": False,
    "domicile_state": "Maharashtra",
    "highest_degree": "B.Tech",
    "stream": "Computer Science",
    "percentage_cgpa": 72.5,
    "passing_year": 2021,
    "graduation_status": "Completed",
    "previous_attempts": 1,
    "raw_resume_text": "phone 9999999999 email private@example.com",
}


async def test_report_saves_sanitized_candidate_and_exam_snapshot(client):
    payload = {
        "exam_id": "ssc-cgl-general",
        "candidate": CANDIDATE,
        "reported_verdict": "ineligible",
        "expected_verdict": "eligible",
        "note": "Age relaxation looks wrong for my category.",
    }

    resp = await client.post(REPORT_URL, json=payload)

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "received"
    assert body["exam_id"] == "ssc-cgl-general"
    assert body["report_id"]

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(EligibilityReport).where(EligibilityReport.id == body["report_id"])
        )
        report = result.scalar_one()

    assert report.exam_id == "ssc-cgl-general"
    assert report.reported_verdict == "ineligible"
    assert report.expected_verdict == "eligible"
    assert report.note == "Age relaxation looks wrong for my category."

    snapshot = report.candidate_snapshot
    assert "full_name" not in snapshot
    assert "raw_resume_text" not in snapshot
    assert snapshot["category"] == "OBC-NCL"
    assert snapshot["highest_degree"] == "B.Tech"
    assert snapshot["previous_attempts"] == 1
    assert snapshot["graduation_status"] == "Completed"

    exam_snapshot = report.exam_snapshot
    assert exam_snapshot["exam_id"] == "ssc-cgl-general"
    assert exam_snapshot["source_url"]
    assert exam_snapshot["last_checked_at"]


async def test_report_for_unknown_exam_returns_404(client):
    payload = {
        "exam_id": "not-a-real-exam",
        "candidate": CANDIDATE,
        "note": "testing 404",
    }

    resp = await client.post(REPORT_URL, json=payload)

    assert resp.status_code == 404


async def test_exam_list_includes_source_metadata(client):
    resp = await client.get(EXAMS_URL)

    assert resp.status_code == 200, resp.text
    exams = resp.json()["exams"]
    assert exams
    for exam in exams:
        assert exam.get("source_url")
        assert exam.get("last_checked_at")


async def test_check_response_has_verdicts_explanations_and_source_metadata(client):
    resp = await client.post(CHECK_URL, json=CANDIDATE)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "check_manually" in body

    all_results = (
        body["eligible_now"]
        + body["borderline_last_chance"]
        + body["ineligible"]
        + body["check_manually"]
    )
    assert all_results

    for item in all_results:
        assert item["verdict"] in {"eligible", "check_manually", "ineligible"}
        assert item["check_manually"] is (item["verdict"] == "check_manually")
        assert item["is_eligible"] is (item["verdict"] == "eligible")
        assert item["source_url"]
        assert item["last_checked_at"]
        assert item["rules"]
        for rule in item["rules"]:
            assert rule["rule"]
            assert rule["candidate_value"]
            assert rule["required_value"]
            assert rule["status"] in {"passed", "failed", "needs_check"}
            assert rule["message"]
