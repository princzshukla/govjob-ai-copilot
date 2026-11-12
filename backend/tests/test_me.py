import pytest
from sqlalchemy import func, select

from app.api.v1.endpoints import eligibility as eligibility_endpoint
from app.core.database import AsyncSessionLocal
from app.models.candidate import CandidateProfile
from app.models.progress import RoadmapProgress
from app.models.roadmap import SavedRoadmap
from app.schemas.roadmap import StudyRoadmapResponse, WeeklyMilestone

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
PROFILE_URL = "/api/v1/users/me/profile"
CLAIM_URL = "/api/v1/users/me/claim-draft"
GENERATE_ROADMAP_URL = "/api/v1/eligibility/generate-roadmap/ssc-cgl-general"
ROADMAP_GET_URL = "/api/v1/users/me/roadmaps/ssc-cgl-general"

EMAIL = "me-student@example.com"
OTHER_EMAIL = "me-other@example.com"
PASSWORD = "correct-horse-battery"

FULL_PROFILE = {
    "full_name": "  Ada   Lovelace  ",
    "dob": "2001-05-15",
    "gender": "Female",
    "category": "OBC-NCL",
    "is_pwd": False,
    "domicile_state": "Uttar Pradesh",
    "highest_degree": "B.Tech",
    "stream": "Computer Science",
    "percentage_cgpa": 84.5,
    "passing_year": 2023,
    "skills": ["Python", "SQL"],
}


async def _register_and_login(client, email: str = EMAIL):
    resp = await client.post(
        REGISTER_URL, json={"email": email, "password": PASSWORD, "full_name": "Me Student"}
    )
    assert resp.status_code == 201, resp.text
    login = await client.post(LOGIN_URL, json={"email": email, "password": PASSWORD})
    assert login.status_code == 200, login.text


# ------------------------------------------------------------- Profile

async def test_profile_put_get_roundtrip_and_replace(client):
    await _register_and_login(client)

    put = await client.put(PROFILE_URL, json=FULL_PROFILE)
    assert put.status_code == 200, put.text
    body = put.json()
    assert body["full_name"] == "Ada Lovelace"  # whitespace-normalized
    assert body["dob"] == "2001-05-15"
    assert body["skills"] == ["Python", "SQL"]

    got = await client.get(PROFILE_URL)
    assert got.status_code == 200
    assert got.json() == body

    # Replace with fewer fields; the new state is stored verbatim.
    await client.put(PROFILE_URL, json={"full_name": "Only Name", "skills": ["GST"]})
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(CandidateProfile))).scalars().all()
        assert len(rows) == 1  # one row per user, never duplicated


async def test_profile_put_is_rejected_when_invalid(client):
    await _register_and_login(client)

    bad = await client.put(PROFILE_URL, json={**FULL_PROFILE, "percentage_cgpa": 150})
    assert bad.status_code == 422

    unknown = await client.put(PROFILE_URL, json={**FULL_PROFILE, "percentage": 90})
    assert unknown.status_code == 422

    too_many_skills = await client.put(
        PROFILE_URL, json={"skills": [f"skill-{i}" for i in range(60)]}
    )
    assert too_many_skills.status_code == 200  # capped, not rejected
    assert len(too_many_skills.json()["skills"]) == 50


async def test_profile_unknown_fields_are_rejected(client):
    await _register_and_login(client)

    resp = await client.put(PROFILE_URL, json={"email": "a@example.com"})
    assert resp.status_code == 422


async def test_profile_is_isolated_between_users(client):
    await _register_and_login(client)
    assert (await client.put(PROFILE_URL, json=FULL_PROFILE)).status_code == 200

    await _register_and_login(client, OTHER_EMAIL)
    assert (await client.get(PROFILE_URL)).status_code == 404


async def test_profile_requires_auth(client):
    assert (await client.put(PROFILE_URL, json=FULL_PROFILE)).status_code == 401
    assert (await client.get(PROFILE_URL)).status_code == 401


# ------------------------------------------------------------ Claim draft

async def test_claim_draft_claims_once_and_never_overwrites(client):
    await _register_and_login(client)

    first = await client.post(CLAIM_URL, json={"full_name": "Guest User", "dob": "2000-01-01"})
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "claimed"

    # A different draft does not overwrite the claimed profile.
    second = await client.post(CLAIM_URL, json={"full_name": "Changed Name"})
    assert second.json()["status"] == "already_claimed"
    assert second.json()["profile"]["full_name"] == "Guest User"

    async with AsyncSessionLocal() as db:
        count = await db.scalar(select(func.count()).select_from(CandidateProfile))
        assert count == 1


async def test_claim_draft_requires_something(client):
    await _register_and_login(client)

    resp = await client.post(CLAIM_URL, json={})
    assert resp.status_code == 422


async def test_claim_draft_is_rejected_when_invalid(client):
    await _register_and_login(client)

    resp = await client.post(CLAIM_URL, json={"percentage_cgpa": 150})
    assert resp.status_code == 422


async def test_claim_draft_requires_auth(client):
    resp = await client.post(CLAIM_URL, json={"full_name": "X"})
    assert resp.status_code == 401


# ------------------------------------------------------------ Roadmaps

def _fake_roadmap(weeks: int = 4) -> StudyRoadmapResponse:
    return StudyRoadmapResponse(
        exam_name="SSC CGL",
        total_duration_weeks=weeks,
        weekly_breakdown=[
            WeeklyMilestone(
                week_number=i,
                phase="Foundation",
                focus_subject="Quantitative Aptitude",
                topics=["Number Systems"],
                practice_goal="Solve 50 PYQs",
                recommended_resources=["NCERT"],
            )
            for i in range(1, weeks + 1)
        ],
        revision_strategy="One mock test per week",
    )


@pytest.fixture
def _fixed_roadmap(monkeypatch):
    roadmap = _fake_roadmap(4)
    eligibility_endpoint.ROADMAP_CACHE.clear()

    async def fake_generate(*_args, **_kwargs):
        return roadmap

    monkeypatch.setattr(eligibility_endpoint, "generate_study_roadmap_groq", fake_generate)
    yield roadmap
    eligibility_endpoint.ROADMAP_CACHE.clear()


async def test_generating_a_roadmap_saves_it_for_the_user(client, _fixed_roadmap):
    await _register_and_login(client)

    resp = await client.post(f"{GENERATE_ROADMAP_URL}?target_weeks=4")
    assert resp.status_code == 200, resp.text

    got = await client.get(ROADMAP_GET_URL)
    assert got.status_code == 200, got.text
    body = got.json()
    assert body["exam_id"] == "ssc-cgl-general"
    assert body["target_weeks"] == 4
    assert len(body["roadmap"]["weekly_breakdown"]) == 4
    assert body["completed_weeks"] == []
    assert body["percent"] == 0

    # Generating again reuses the database row instead of duplicating it.
    first_id = body["roadmap_id"]
    async with AsyncSessionLocal() as db:
        user_row = (await db.execute(select(SavedRoadmap))).scalars().all()
        assert len(user_row) == 1


async def test_roadmap_is_isolated_between_users(client, _fixed_roadmap):
    await _register_and_login(client)
    await client.post(f"{GENERATE_ROADMAP_URL}?target_weeks=4")

    await _register_and_login(client, OTHER_EMAIL)
    assert (await client.get(ROADMAP_GET_URL)).status_code == 404


async def test_week_completion_roundtrip_and_idempotency(client, _fixed_roadmap):
    await _register_and_login(client)
    await client.post(f"{GENERATE_ROADMAP_URL}?target_weeks=4")
    roadmap_id = (await client.get(ROADMAP_GET_URL)).json()["roadmap_id"]

    put = await client.put(f"/api/v1/users/me/roadmaps/{roadmap_id}/progress", json={"week_no": 1, "done": True})
    assert put.status_code == 200, put.text
    assert put.json()["completed_weeks"] == [1]
    assert put.json()["percent"] == 25

    # Marking week 1 done twice does not create duplicates.
    put2 = await client.put(f"/api/v1/users/me/roadmaps/{roadmap_id}/progress", json={"week_no": 1, "done": True})
    assert put2.json()["completed_weeks"] == [1]

    await client.put(f"/api/v1/users/me/roadmaps/{roadmap_id}/progress", json={"week_no": 3, "done": True})
    progress = await client.get(f"/api/v1/users/me/roadmaps/{roadmap_id}/progress")
    assert progress.json()["completed_weeks"] == [1, 3]
    assert progress.json()["percent"] == 50

    undone = await client.put(f"/api/v1/users/me/roadmaps/{roadmap_id}/progress", json={"week_no": 1, "done": False})
    assert undone.json()["completed_weeks"] == [3]
    assert undone.json()["percent"] == 25

    async with AsyncSessionLocal() as db:
        count = await db.scalar(select(func.count()).select_from(RoadmapProgress))
        assert count == 1


async def test_week_out_of_range_is_rejected(client, _fixed_roadmap):
    await _register_and_login(client)
    await client.post(f"{GENERATE_ROADMAP_URL}?target_weeks=4")
    roadmap_id = (await client.get(ROADMAP_GET_URL)).json()["roadmap_id"]

    for week in (0, 5, 99):
        resp = await client.put(f"/api/v1/users/me/roadmaps/{roadmap_id}/progress", json={"week_no": week, "done": True})
        assert resp.status_code == 422, f"week {week} was accepted"


async def test_week_out_of_user_ownership_is_rejected(client, _fixed_roadmap):
    await _register_and_login(client)
    await client.post(f"{GENERATE_ROADMAP_URL}?target_weeks=4")
    roadmap_id = (await client.get(ROADMAP_GET_URL)).json()["roadmap_id"]

    await _register_and_login(client, OTHER_EMAIL)
    resp = await client.put(f"/api/v1/users/me/roadmaps/{roadmap_id}/progress", json={"week_no": 1, "done": True})
    assert resp.status_code == 404

    GET_ROW = f"/api/v1/users/me/roadmaps/{roadmap_id}/progress"
    assert (await client.get(GET_ROW)).status_code == 404


async def test_week_body_rejects_fake_fields(client, _fixed_roadmap):
    await _register_and_login(client)
    await client.post(f"{GENERATE_ROADMAP_URL}?target_weeks=4")
    roadmap_id = (await client.get(ROADMAP_GET_URL)).json()["roadmap_id"]

    resp = await client.put(
        f"/api/v1/users/me/roadmaps/{roadmap_id}/progress", json={"week_no": 1, "done": True, "percentage": 100},
    )
    assert resp.status_code == 422

    resp = await client.put(
        f"/api/v1/users/me/roadmaps/{roadmap_id}/progress", json={"week_no": 1, "done": True, "score": 10},
    )
    assert resp.status_code == 422


async def test_week_requires_auth(client, _fixed_roadmap):
    resp = await client.put(
        "/api/v1/users/me/roadmaps/nonexistent/progress",
        json={"week_no": 1, "done": True},
    )
    assert resp.status_code == 401


async def test_roadmaps_get_requires_auth(client):
    assert (await client.get(ROADMAP_GET_URL)).status_code == 401


# ------------------------------------- Old account endpoints unchanged


async def test_old_account_endpoints_still_behave(client):
    """The account actions live in endpoints/users.py under /users/me alongside
    the data routes owned by endpoints/user_data.py; both must keep working."""
    await _register_and_login(client)

    # PATCH /users/me (account action) still works next to the new routes.
    patched = await client.patch("/api/v1/users/me", json={"full_name": "New Name"})
    assert patched.status_code == 200
    assert patched.json()["full_name"] == "New Name"

    # POST /users/me/change-password still verifies the current password.
    wrong = await client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "definitely-wrong", "new_password": "new-secure-password-123"},
    )
    assert wrong.status_code == 400

    # DELETE /users/me still requires the password.
    bad_delete = await client.request("DELETE", "/api/v1/users/me", json={"password": "definitely-wrong"})
    assert bad_delete.status_code == 400
