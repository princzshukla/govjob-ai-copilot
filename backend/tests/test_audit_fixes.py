"""Regression tests for the external LLM/auth-boundary review.

Covers the paths touched by the audit: the LLM boundary, submit scoring and
the registration/profile flows that these phases implemented.
"""

import json
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.api.v1.endpoints import eligibility as eligibility_endpoint  # noqa: F401  (ensures import order matches conftest)
from app.core.database import AsyncSessionLocal
from app.models.adaptive import QuestionBank, TopicMastery
from app.services import quiz_service

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
SUBMIT_URL = "/api/v1/adaptive/submit-quiz"
QUIZ_URL = "/api/v1/adaptive/quiz"

EMAIL = "audit-student@example.com"
PASSWORD = "correct-horse-battery"
FULL_PROFILE = {
    "full_name": "Audit Student",
    "dob": "2000-04-01",
    "category": "OBC-NCL",
    "domicile_state": "Uttar Pradesh",
    "highest_degree": "B.Tech",
    "percentage_cgpa": 70.0,
}


async def _register_and_login(client, email: str = EMAIL):
    resp = await client.post(
        REGISTER_URL, json={"email": email, "password": PASSWORD, "full_name": "Audit Student"}
    )
    assert resp.status_code == 201, resp.text


def _question_bank_row(**overrides) -> QuestionBank:
    data = {
        "question": "What is 2 + 2? Simple addition.",
        "options": {"A": "3", "B": "4", "C": "5", "D": "6"},
        "correct_option": "B",
        "explanation": "Basic addition.",
        "expected_time_sec": 30,
    }
    data.update(overrides.pop("question_data", {}))
    row = QuestionBank(
        id=overrides.pop("id", "audit-q-1"),
        exam_id=overrides.pop("exam_id", "ssc-cgl-tier1"),
        subject=overrides.pop("subject", "Quantitative Aptitude"),
        topic=overrides.pop("topic", "Percentage"),
        sub_topic=overrides.pop("sub_topic", "Successive Percentage"),
        difficulty=overrides.pop("difficulty", "Easy"),
        question_data=data,
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


class _FakeCompletions:
    def __init__(self, content: str):
        self._content = content

    async def create(self, **_kwargs):
        message = SimpleNamespace(content=self._content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class _FakeClient:
    """Minimal stand-in for AsyncGroq; never performs network calls."""

    def __init__(self, content: str):
        self.chat = SimpleNamespace(completions=_FakeCompletions(content))


# ---------------------------------------------------------- LLM boundary

async def test_llm_output_is_normalised_before_caching(client, monkeypatch):
    questions = [
        {
            "sub_topic": "Number Systems",
            "question": "A normal, well-formed question about addition?",
            "options": {"A": "3", "B": "4", "C": "5", "D": "6"},
            "correct_option": "B",
            "explanation": "Basic addition.",
            "difficulty": "Easy",
            "expected_time_sec": 30,
        },
        {
            # Null fields everywhere the model commonly fails to fill.
            "sub_topic": None,
            "question": "What is 10 x 10? Simple multiplication question.",
            "options": ["100", "110", "90", "10"],
            "correct_option": "a",
            "explanation": None,
            "difficulty": "Impossible",
            "expected_time_sec": None,
        },
        {
            # correct_option not present in options: unusable, must be skipped.
            "sub_topic": "Divisibility",
            "question": "Which number is divisible by 3? Choose one.",
            "options": {"A": "3", "B": "4", "C": "5", "D": "7"},
            "correct_option": "2",
            "explanation": "3 % 3 == 0.",
            "difficulty": "Medium",
            "expected_time_sec": 20,
        },
    ]
    monkeypatch.setattr(
        quiz_service, "groq_client", _FakeClient(json.dumps({"questions": questions}))
    )

    async with AsyncSessionLocal() as db:
        items = await quiz_service.get_or_generate_quiz(
            db=db,
            exam_id="ssc-cgl-tier1",
            subject="Quantitative Aptitude",
            topic="Percentage",
            count=2,
        )

    assert len(items) == 2
    weird = next(i for i in items if i.question.startswith("What is 10"))
    assert weird.options == {"A": "100", "B": "110", "C": "90", "D": "10"}
    assert weird.sub_topic == "Percentage"  # falls back to the requested topic
    assert weird.difficulty == "Medium"  # unsupported difficulty normalised
    assert weird.expected_time_sec >= 1

    # The poisoned row was never persisted or served to another account.
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(QuestionBank))).scalars().all()
        assert len(rows) == 2
        assert all(
            str((r.question_data or {}).get("correct_option", "")).upper() in ("A", "B", "C", "D")
            for r in rows
        )


async def test_markdown_fenced_json_raises_typed_error(client, monkeypatch):
    fenced = "```json\n{}\n```"
    monkeypatch.setattr(quiz_service, "groq_client", _FakeClient(fenced))

    async with AsyncSessionLocal() as db:
        with pytest.raises(quiz_service.QuizGenerationError):
            await quiz_service.get_or_generate_quiz(
                db=db,
                exam_id="ssc-cgl-tier1",
                subject="Quantitative Aptitude",
                topic="Percentage",
                count=1,
            )


async def test_empty_question_list_raises_typed_error(client, monkeypatch):
    monkeypatch.setattr(quiz_service, "groq_client", _FakeClient('{"questions": []}'))

    async with AsyncSessionLocal() as db:
        with pytest.raises(quiz_service.QuizGenerationError):
            await quiz_service.get_or_generate_quiz(
                db=db,
                exam_id="ssc-cgl-tier1",
                subject="Quantitative Aptitude",
                topic="Percentage",
                count=1,
            )


async def test_cache_query_is_scoped_by_subject(client, monkeypatch):
    async with AsyncSessionLocal() as db:
        for i in range(3):
            db.add(_question_bank_row(id=f"sub-q-{i}"))
        await db.commit()

    # groq unavailable: an unmatched subject must NOT serve the other's rows.
    monkeypatch.setattr(quiz_service, "groq_client", None)
    async with AsyncSessionLocal() as db:
        with pytest.raises(quiz_service.QuizGenerationError):
            await quiz_service.get_or_generate_quiz(
                db=db,
                exam_id="ssc-cgl-tier1",
                subject="General Intelligence",
                topic="Percentage",
                count=3,
            )

    async with AsyncSessionLocal() as db:
        items = await quiz_service.get_or_generate_quiz(
            db=db,
            exam_id="ssc-cgl-tier1",
            subject="Quantitative Aptitude",
            topic="Percentage",
            count=3,
        )
        assert len(items) == 3


async def test_quiz_generation_params_must_match_whitelist(client):
    await _register_and_login(client)
    resp = await client.get(
        QUIZ_URL,
        params={"exam_id": "x'; DROP TABLE users;--", "subject": "Percentage", "topic": "y"},
    )
    assert resp.status_code == 422

    resp = await client.get(
        QUIZ_URL,
        params={"exam_id": "ssc-cgl-tier1", "subject": "Quantitative Aptitude", "topic": "Percentage; DROP TABLE users"},
    )
    assert resp.status_code == 422


# --------------------------------------------------------- Scoring paths

async def test_duplicate_question_ids_are_counted_once(client):
    await _register_and_login(client)
    async with AsyncSessionLocal() as db:
        db.add(_question_bank_row(id="dup-q-1"))
        await db.commit()

    resp = await client.post(
        SUBMIT_URL,
        json={
            "exam_id": "ssc-cgl-tier1",
            "topic": "Percentage",
            "answers": [
                {"question_id": "dup-q-1", "selected_option": "B", "time_taken_sec": 10},
                {"question_id": "dup-q-1", "selected_option": "B", "time_taken_sec": 10},
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_attempted"] == 1
    assert body["correct_count"] == 1


async def test_time_taken_ignores_unknown_question_ids(client):
    await _register_and_login(client)
    async with AsyncSessionLocal() as db:
        db.add(_question_bank_row(id="known-q-1"))
        await db.commit()

    resp = await client.post(
        SUBMIT_URL,
        json={
            "exam_id": "ssc-cgl-tier1",
            "topic": "Percentage",
            "answers": [
                {"question_id": "known-q-1", "selected_option": "B", "time_taken_sec": 10},
                {"question_id": "ghost-q-1", "selected_option": "B", "time_taken_sec": 2000},
            ],
        },
    )
    assert resp.status_code == 200, resp.text

    async with AsyncSessionLocal() as db:
        from app.models.adaptive import QuizAttempt

        time_taken = await db.scalar(
            select(QuizAttempt.time_taken_seconds).order_by(QuizAttempt.created_at.desc()).limit(1)
        )
        assert time_taken == 10


async def test_mastery_has_one_row_per_user_exam_topic(client):
    await _register_and_login(client)
    async with AsyncSessionLocal() as db:
        for i in range(2):
            db.add(_question_bank_row(id=f"mastery-q-{i}", topic="Percentage"))
        await db.commit()

    for _ in range(2):
        answers = [
            {"question_id": qid, "selected_option": "B", "time_taken_sec": 5}
            for qid in ("mastery-q-0", "mastery-q-1")
        ]
        resp = await client.post(
            SUBMIT_URL,
            json={"exam_id": "ssc-cgl-tier1", "topic": "Percentage", "answers": answers},
        )
        assert resp.status_code == 200, resp.text

    async with AsyncSessionLocal() as db:
        count = await db.scalar(select(func.count()).select_from(TopicMastery))
        assert count == 1


# ------------------------------------------------------ Auth & profile

async def test_register_sets_session_cookie(client):
    resp = await client.post(
        REGISTER_URL,
        json={"email": EMAIL, "password": PASSWORD, "full_name": "Audit Student"},
    )
    assert resp.status_code == 201, resp.text
    assert "set-cookie" in {k.lower() for k in resp.headers}

    # The session cookie is immediately usable.
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == EMAIL


async def test_duplicate_registration_is_a_generic_409(client):
    resp1 = await client.post(
        REGISTER_URL,
        json={"email": EMAIL, "password": PASSWORD, "full_name": "Audit Student"},
    )
    assert resp1.status_code == 201

    resp = await client.post(
        REGISTER_URL,
        json={"email": EMAIL, "password": PASSWORD, "full_name": "Audit Student"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "An account with this email or phone already exists"
    # Nothing in the body distinguishes email-vs-phone as the colliding identifier.


async def test_partial_profile_put_merges_and_does_not_wipe(client):
    await _register_and_login(client)
    await client.put("/api/v1/users/me/profile", json=FULL_PROFILE)

    resp = await client.put("/api/v1/users/me/profile", json={"full_name": "Only Name"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["full_name"] == "Only Name"
    assert body["dob"] == "2000-04-01"  # unchanged
    assert body["category"] == "OBC-NCL"  # unchanged
    assert body["percentage_cgpa"] == 70.0  # unchanged
