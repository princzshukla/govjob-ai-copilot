from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

from app.api.v1.endpoints import candidate as candidate_endpoint
from app.api.v1.endpoints import notifications as notifications_endpoint
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.adaptive import QuestionBank, QuizAttempt, TopicMastery
from app.models.auth import User
from app.models.telegram import TelegramLink, TelegramLinkCode
from app.schemas.candidate import ParsedResumeProfile, ResumeParseResponse

PASSWORD = "correct-horse-battery"
EMAIL_A = "a@example.com"
EMAIL_B = "b@example.com"

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ADAPTIVE_QUIZ_URL = "/api/v1/adaptive/quiz"
ADAPTIVE_SUBMIT_URL = "/api/v1/adaptive/submit-quiz"
MASTERY_URL = "/api/v1/adaptive/mastery/ssc-cgl-tier1"
ROADMAP_URL = "/api/v1/eligibility/generate-roadmap/ssc-cgl-general"
SYNC_URL = "/api/v1/eligibility/sync-live-jobs"
CHECK_URL = "/api/v1/eligibility/check"
UPLOAD_URL = "/api/v1/candidate/parse-resume"
ALERT_URL = "/api/v1/notifications/send-deadline-alert"
LINK_URL = "/api/v1/notifications/telegram/link"
STATUS_URL = "/api/v1/notifications/telegram/status"
WEBHOOK_URL = "/api/v1/notifications/telegram/webhook"


async def _register(client, email: str = EMAIL_A) -> None:
    """Create the account and open a session for it.

    Register itself does not set a cookie (users must sign in), so the helper
    logs in immediately: every test below needs an authenticated client.
    """
    resp = await client.post(REGISTER_URL, json={"email": email, "password": PASSWORD})
    assert resp.status_code == 201, resp.text
    await _login(client, email)


async def _login(client, email: str = EMAIL_A) -> None:
    resp = await client.post(LOGIN_URL, json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200, resp.text


async def _user_id(email: str = EMAIL_A) -> int:
    async with AsyncSessionLocal() as db:
        user_id = await db.scalar(select(User.id).where(User.email == email))
        assert user_id is not None
        return user_id


async def _seed_questions(n: int = 2) -> list[str]:
    async with AsyncSessionLocal() as db:
        for i in range(n):
            db.add(
                QuestionBank(
                    id=f"q-test-{i}",
                    exam_id="ssc-cgl-tier1",
                    subject="Quantitative Aptitude",
                    topic="Percentage",
                    sub_topic="Basics",
                    difficulty="Easy",
                    question_data={
                        "question": "What is 2 + 2?",
                        "options": {"A": "3", "B": "4", "C": "5", "D": "6"},
                        "correct_option": "B",
                        "explanation": "Basic addition.",
                        "expected_time_sec": 10,
                    },
                )
            )
        await db.commit()
    return [f"q-test-{i}" for i in range(n)]


def _answers(question_ids: list[str], option: str = "B") -> list[dict]:
    return [
        {"question_id": qid, "selected_option": option, "time_taken_sec": 5}
        for qid in question_ids
    ]


async def test_protected_routes_require_auth(client):
    calls = [
        ("GET", ADAPTIVE_QUIZ_URL + "?exam_id=x&subject=y&topic=z", None),
        (
            "POST",
            ADAPTIVE_SUBMIT_URL,
            {
                "exam_id": "x",
                "topic": "y",
                "answers": [
                    {"question_id": "q", "selected_option": "B", "time_taken_sec": 1}
                ],
            },
        ),        ("GET", MASTERY_URL, None),
        ("POST", ROADMAP_URL, None),
        ("POST", SYNC_URL, None),
        ("POST", ALERT_URL, {"exam_title": "x", "application_deadline": "2026-01-01", "days_left": 1}),
        ("POST", LINK_URL, None),
        ("GET", STATUS_URL, None),
        ("DELETE", LINK_URL, None),
    ]

    for method, url, body in calls:
        resp = await client.request(method, url, json=body)
        assert resp.status_code == 401, f"{method} {url} returned {resp.status_code}"


async def test_tampered_cookie_is_logged_out(client):
    await _register(client)
    client.cookies.set(settings.COOKIE_NAME, "not-a-real-session-token")

    resp = await client.get(MASTERY_URL)

    assert resp.status_code == 401


async def test_quiz_response_never_leaks_answers(client):
    await _register(client)
    await _seed_questions()

    resp = await client.get(
        ADAPTIVE_QUIZ_URL,
        params={
            "exam_id": "ssc-cgl-tier1",
            "subject": "Quantitative Aptitude",
            "topic": "Percentage",
            "count": 2,
        },
    )

    assert resp.status_code == 200, resp.text
    questions = resp.json()["questions"]
    assert questions
    for question in questions:
        assert "correct_option" not in question
        assert "explanation" not in question


async def test_submit_uses_session_owner_and_server_score(client):
    await _register(client)
    question_ids = await _seed_questions(2)
    user_a = await _user_id()

    resp = await client.post(
        ADAPTIVE_SUBMIT_URL,
        json={
            # These must be ignored: only the cookie decides the owner and the
            # stored question rows decide the score.
            "user_id": 99999,
            "score": 0,
            "exam_id": "ssc-cgl-tier1",
            "topic": "Percentage",
            "answers": _answers(question_ids),
        },
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["correct_count"] == 2
    assert body["accuracy_pct"] == 100.0
    assert {r["correct_option"] for r in body["results"]} == {"B"}

    async with AsyncSessionLocal() as db:
        attempt_owner = await db.scalar(select(QuizAttempt.user_id))
        mastery_owner = await db.scalar(select(TopicMastery.user_id))
        attempt_score = await db.scalar(select(QuizAttempt.score))

    assert attempt_owner == user_a
    assert mastery_owner == user_a
    assert attempt_score == 2


async def test_submit_rejects_questions_from_another_drill(client):
    await _register(client)
    question_ids = await _seed_questions(1)

    resp = await client.post(
        ADAPTIVE_SUBMIT_URL,
        json={
            "exam_id": "a-different-exam",
            "topic": "Percentage",
            "answers": _answers(question_ids),
        },
    )

    assert resp.status_code == 400


async def test_mastery_is_isolated_between_users(client):
    await _register(client)
    question_ids = await _seed_questions(1)
    submit = await client.post(
        ADAPTIVE_SUBMIT_URL,
        json={
            "exam_id": "ssc-cgl-tier1",
            "topic": "Percentage",
            "answers": _answers(question_ids),
        },
    )
    assert submit.status_code == 200, submit.text

    mine = await client.get(MASTERY_URL)
    assert mine.status_code == 200
    assert mine.json()["user_id"] == await _user_id()
    assert len(mine.json()["topics"]) == 1

    # Registering someone else replaces the session cookie.
    await _register(client, EMAIL_B)
    theirs = await client.get(MASTERY_URL)

    assert theirs.status_code == 200
    assert theirs.json()["user_id"] == await _user_id(EMAIL_B)
    assert theirs.json()["topics"] == []


async def test_deleting_user_cascades_adaptive_rows(client):
    await _register(client)
    question_ids = await _seed_questions(1)
    await client.post(
        ADAPTIVE_SUBMIT_URL,
        json={
            "exam_id": "ssc-cgl-tier1",
            "topic": "Percentage",
            "answers": _answers(question_ids),
        },
    )
    user_a = await _user_id()

    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_a))
        await db.commit()
        attempts = await db.scalar(select(func.count()).select_from(QuizAttempt))
        mastery = await db.scalar(select(func.count()).select_from(TopicMastery))

    assert attempts == 0
    assert mastery == 0


async def test_upload_rejects_non_pdf_and_oversized_files(client):
    wrong_type = await client.post(
        UPLOAD_URL, files={"file": ("resume.pdf", b"%PDF-1.4", "text/plain")}
    )
    assert wrong_type.status_code == 400

    fake_pdf = await client.post(
        UPLOAD_URL, files={"file": ("resume.pdf", b"not a pdf at all", "application/pdf")}
    )
    assert fake_pdf.status_code == 400

    oversized = await client.post(
        UPLOAD_URL,
        files={"file": ("resume.pdf", b"%PDF-" + b"0" * (5 * 1024 * 1024), "application/pdf")},
    )
    assert oversized.status_code == 413


async def test_guest_upload_quota_is_three_per_day(client, monkeypatch):
    async def fake_parse(_text: str) -> ResumeParseResponse:
        return ResumeParseResponse(
            extracted_profile=ParsedResumeProfile(),
            is_complete_for_gov_jobs=False,
            missing_fields=[],
            message="ok",
        )

    monkeypatch.setattr(candidate_endpoint, "extract_raw_text_from_pdf", lambda _b: "resume")
    monkeypatch.setattr(candidate_endpoint, "parse_resume_with_groq", fake_parse)

    for _ in range(3):
        resp = await client.post(
            UPLOAD_URL, files={"file": ("resume.pdf", b"%PDF-1.4 fake", "application/pdf")}
        )
        assert resp.status_code == 200, resp.text

    blocked = await client.post(
        UPLOAD_URL, files={"file": ("resume.pdf", b"%PDF-1.4 fake", "application/pdf")}
    )
    assert blocked.status_code == 429


async def test_eligibility_check_stays_open_to_guests(client):
    resp = await client.post(
        CHECK_URL,
        json={
            "dob": "2000-01-01",
            "category": "General",
            "domicile_state": "Uttar Pradesh",
            "highest_degree": "B.Tech",
            "percentage_cgpa": 75.0,
        },
    )

    assert resp.status_code == 200, resp.text


async def test_live_job_sync_cooldown_and_generic_errors(client, monkeypatch):
    from app.services import job_scraper

    async def empty_fetch():
        return []

    async def empty_structure(_raw):
        return []

    monkeypatch.setattr(job_scraper, "fetch_raw_job_listings", empty_fetch)
    monkeypatch.setattr(job_scraper, "structure_jobs_with_groq", empty_structure)

    await _register(client)
    first = await client.post(SYNC_URL)
    assert first.status_code == 200, first.text

    second = await client.post(SYNC_URL)
    assert second.status_code == 429
    assert "Retry-After" in second.headers


async def test_live_job_sync_error_is_not_echoed(client, monkeypatch):
    from app.services import job_scraper

    async def failing_fetch():
        raise RuntimeError("internal-secret-detail")

    monkeypatch.setattr(job_scraper, "fetch_raw_job_listings", failing_fetch)

    await _register(client)
    resp = await client.post(SYNC_URL)

    assert resp.status_code == 502
    assert "internal-secret-detail" not in resp.text


async def test_telegram_link_flow_and_alert_destination(client, monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "test-webhook-secret")
    monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "govjob_test_bot")
    await _register(client)

    start = await client.post(LINK_URL)
    assert start.status_code == 200, start.text
    code = start.json()["code"]
    assert start.json()["bot_username"] == "govjob_test_bot"

    # A webhook call without the secret header must be rejected.
    no_secret = await client.post(
        WEBHOOK_URL,
        json={"message": {"chat": {"id": 111}, "text": f"/start {code}"}},
    )
    assert no_secret.status_code == 403

    linked = await client.post(
        WEBHOOK_URL,
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
        json={"message": {"chat": {"id": 123456789}, "text": f"/start {code}"}},
    )
    assert linked.status_code == 200, linked.text

    status_resp = await client.get(STATUS_URL)
    assert status_resp.status_code == 200
    assert status_resp.json()["linked"] is True
    assert status_resp.json()["chat_id"].endswith("6789")

    # The same code cannot claim a second chat.
    await client.post(
        WEBHOOK_URL,
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
        json={"message": {"chat": {"id": 999}, "text": code}},
    )
    async with AsyncSessionLocal() as db:
        assert await db.scalar(select(TelegramLink.chat_id)) == "123456789"

    captured: dict[str, str] = {}

    async def fake_send(chat_id: str, message: str) -> bool:
        captured["chat_id"] = chat_id
        captured["message"] = message
        return True

    monkeypatch.setattr(notifications_endpoint, "send_telegram_alert", fake_send)

    alert = await client.post(
        ALERT_URL,
        json={
            # Ignored on purpose: the destination comes from telegram_links.
            "chat_id": "999",
            "exam_title": "SSC CGL 2026",
            "application_deadline": "2026-12-31",
            "days_left": 10,
        },
    )
    assert alert.status_code == 200, alert.text
    assert captured["chat_id"] == "123456789"
    assert "999" != captured["chat_id"]

    assert (await client.delete(LINK_URL)).status_code == 200
    assert (await client.get(STATUS_URL)).json()["linked"] is False
    assert (await client.post(ALERT_URL, json={
        "exam_title": "SSC CGL 2026",
        "application_deadline": "2026-12-31",
        "days_left": 10,
    })).status_code == 409


async def test_expired_telegram_code_is_ignored(client, monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "test-webhook-secret")
    await _register(client)

    code = (await client.post(LINK_URL)).json()["code"]

    async with AsyncSessionLocal() as db:
        row = await db.scalar(select(TelegramLinkCode))
        row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await db.commit()

    resp = await client.post(
        WEBHOOK_URL,
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"},
        json={"message": {"chat": {"id": 555}, "text": code}},
    )

    assert resp.status_code == 200
    assert (await client.get(STATUS_URL)).json()["linked"] is False
