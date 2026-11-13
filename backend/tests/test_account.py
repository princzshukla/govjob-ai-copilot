import httpx
from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.main import app
from app.models.adaptive import QuizAttempt, QuestionBank, TopicMastery
from app.models.candidate import CandidateProfile
from app.models.auth import Session, User
from app.models.roadmap import SavedRoadmap
from app.models.telegram import TelegramLink

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"
USERS_ME_URL = "/api/v1/users/me"
CHANGE_PASSWORD_URL = "/api/v1/users/me/change-password"

EMAIL = "student@example.com"
PASSWORD = "correct-horse-battery"
NEW_PASSWORD = "new-correct-horse-battery"


async def _register(client, email: str = EMAIL, password: str = PASSWORD, full_name="Test User", phone=None):
    body = {"email": email, "password": password, "full_name": full_name}
    if phone is not None:
        body["phone"] = phone
    return await client.post(REGISTER_URL, json=body)


async def _register_and_login(client, email: str = EMAIL, password: str = PASSWORD):
    resp = await _register(client, email=email, password=password)
    assert resp.status_code == 201, resp.text
    login = await client.post(LOGIN_URL, json={"email": email, "password": password})
    assert login.status_code == 200, login.text


async def _second_session(email: str = EMAIL, password: str = PASSWORD) -> httpx.AsyncClient:
    """An independent client (own cookie jar) holding another session."""
    transport = httpx.ASGITransport(app=app)
    other = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    login = await other.post(LOGIN_URL, json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return other


async def _user_id(email: str = EMAIL) -> int:
    async with AsyncSessionLocal() as db:
        user_id = await db.scalar(select(User.id).where(User.email == email))
        assert user_id is not None
        return user_id


async def test_register_requires_full_name(client):
    resp = await client.post(REGISTER_URL, json={"email": EMAIL, "password": PASSWORD})
    assert resp.status_code == 422

    resp = await client.post(
        REGISTER_URL, json={"email": EMAIL, "password": PASSWORD, "full_name": "   "}
    )
    assert resp.status_code == 422


async def test_register_normalizes_full_name_and_phone(client):
    resp = await _register(
        client, full_name="  Ada   Lovelace ", phone="98765 43210"
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["full_name"] == "Ada Lovelace"
    assert body["phone"] == "+919876543210"


async def test_register_silently_prefixes_country_code(client):
    resp = await _register(client, phone="9876543210")

    assert resp.status_code == 201, resp.text
    assert resp.json()["phone"] == "+919876543210"


async def test_register_rejects_phone_with_country_code_and_bad_digits(client):
    for bad in ("+919876543210", "1234567890", "987654"):
        resp = await _register(client, phone=bad)
        assert resp.status_code == 422, f"bad phone {bad} was accepted"


async def test_patch_me_updates_full_name_only(client):
    await _register_and_login(client)

    resp = await client.patch(USERS_ME_URL, json={"full_name": "  Ada   Lovelace  "})

    assert resp.status_code == 200, resp.text
    assert resp.json()["full_name"] == "Ada Lovelace"
    assert resp.json()["email"] == EMAIL


async def test_patch_me_rejects_email_phone_id_and_unknown_fields(client):
    await _register_and_login(client)
    before = await client.get(ME_URL)

    for field, value in [
        ("email", "attacker@example.com"),
        ("phone", "+910000000000"),
        ("id", 999),
        ("role", "admin"),
    ]:
        resp = await client.patch(USERS_ME_URL, json={field: value})
        assert resp.status_code == 422, f"{field} was accepted"

    after = await client.get(ME_URL)
    assert after.json() == before.json()


async def test_patch_me_requires_auth(client):
    resp = await client.patch(USERS_ME_URL, json={"full_name": "Nobody"})
    assert resp.status_code == 401


async def test_change_password_wrong_current_changes_nothing(client):
    await _register_and_login(client)

    resp = await client.post(
        CHANGE_PASSWORD_URL,
        json={"current_password": "definitely-wrong", "new_password": NEW_PASSWORD},
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid password"
    # Old password still works, new one still doesn't.
    assert (await client.post(LOGIN_URL, json={"email": EMAIL, "password": PASSWORD})).status_code == 200


async def test_change_password_revokes_other_sessions_keeps_current(client):
    await _register_and_login(client)
    other = await _second_session()
    try:
        assert (await other.get(ME_URL)).status_code == 200

        resp = await client.post(
            CHANGE_PASSWORD_URL,
            json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        )
        assert resp.status_code == 200, resp.text

        # The other session is dead, the current one still works.
        assert (await other.get(ME_URL)).status_code == 401
        assert (await client.get(ME_URL)).status_code == 200
    finally:
        await other.aclose()


async def test_change_password_validates_new_password(client):
    await _register_and_login(client)

    short = await client.post(
        CHANGE_PASSWORD_URL,
        json={"current_password": PASSWORD, "new_password": "short"},
    )
    assert short.status_code == 422

    long_ = await client.post(
        CHANGE_PASSWORD_URL,
        json={"current_password": PASSWORD, "new_password": "x" * 129},
    )
    assert long_.status_code == 422


async def test_change_password_requires_auth(client):
    resp = await client.post(
        CHANGE_PASSWORD_URL,
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert resp.status_code == 401


async def test_delete_me_wrong_password_changes_nothing(client):
    await _register_and_login(client)

    resp = await client.request("DELETE", USERS_ME_URL, json={"password": "definitely-wrong"})

    assert resp.status_code == 400
    assert (await client.get(ME_URL)).status_code == 200


async def test_delete_me_clears_cookie_deletes_user_allows_reregister(client):
    await _register_and_login(client)
    user_id = await _user_id()

    resp = await client.request("DELETE", USERS_ME_URL, json={"password": PASSWORD})

    assert resp.status_code == 204
    set_cookie = resp.headers.get_list("set-cookie")
    assert any(settings.COOKIE_NAME in header for header in set_cookie)

    # Old cookie can no longer authenticate even if replayed.
    assert (await client.get(ME_URL)).status_code == 401

    async with AsyncSessionLocal() as db:
        remaining_sessions = await db.scalar(
            select(func.count()).select_from(Session).where(Session.user_id == user_id)
        )
        assert remaining_sessions == 0
        assert await db.get(User, user_id) is None

    # Email is free to register again.
    re_registered = await _register(client)
    assert re_registered.status_code == 201


async def test_delete_me_removes_related_rows(client):
    await _register_and_login(client)
    user_id = await _user_id()

    question_id = "q-account-delete-test"
    async with AsyncSessionLocal() as db:
        db.add(
            QuestionBank(
                id=question_id,
                exam_id="ssc-cgl-tier1",
                subject="Quantitative Aptitude",
                topic="Percentage",
                sub_topic="Basics",
                difficulty="Easy",
                question_data={
                    "question": "2 + 2?",
                    "options": {"A": "3", "B": "4", "C": "5", "D": "6"},
                    "correct_option": "B",
                    "explanation": "Basic addition.",
                    "expected_time_sec": 10,
                },
            )
        )
        await db.commit()

    submit = await client.post(
        "/api/v1/adaptive/submit-quiz",
        json={
            "exam_id": "ssc-cgl-tier1",
            "topic": "Percentage",
            "answers": [{"question_id": question_id, "selected_option": "B", "time_taken_sec": 5}],
        },
    )
    assert submit.status_code == 200, submit.text

    resp = await client.request("DELETE", USERS_ME_URL, json={"password": PASSWORD})
    assert resp.status_code == 204

    async with AsyncSessionLocal() as db:
        for model in (Session, CandidateProfile, SavedRoadmap, TelegramLink,
                      QuizAttempt, TopicMastery):
            remaining = await db.scalar(
                select(func.count()).select_from(model).where(model.user_id == user_id)
            )
            assert remaining == 0, f"{model.__tablename__} rows survived deletion"


async def test_delete_me_requires_auth(client):
    resp = await client.request("DELETE", USERS_ME_URL, json={"password": PASSWORD})
    assert resp.status_code == 401
