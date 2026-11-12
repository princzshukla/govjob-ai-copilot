import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_session_token
from app.models.auth import Session, User

EMAIL = "student@example.com"
PASSWORD = "correct-horse-battery"

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
LOGOUT_URL = "/api/v1/auth/logout"
ME_URL = "/api/v1/auth/me"


async def register(client, email: str = EMAIL, password: str = PASSWORD):
    return await client.post(REGISTER_URL, json={"email": email, "password": password})


async def login(client, email: str = EMAIL, password: str = PASSWORD):
    return await client.post(LOGIN_URL, json={"email": email, "password": password})


async def test_register_success(client):
    resp = await register(client, email="  Student@Example.COM  ", password=PASSWORD)

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "student@example.com"  # trimmed + lowercased
    assert "password" not in body and "password_hash" not in body

    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == "student@example.com"))
        assert user is not None
        assert user.password_hash.startswith("$argon2id$")  # Argon2id only


async def test_duplicate_email_rejected(client):
    assert (await register(client)).status_code == 201

    # Different case still hits the same unique row after normalization.
    resp = await register(client, email="STUDENT@example.com")

    assert resp.status_code == 409


async def test_wrong_password_rejected(client):
    await register(client)

    resp = await login(client, password="definitely-wrong")

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"
    assert settings.COOKIE_NAME not in resp.cookies


async def test_unknown_email_same_error_as_wrong_password(client):
    await register(client)
    wrong_password = await login(client, password="definitely-wrong")
    unknown_email = await login(client, email="nobody@example.com", password="definitely-wrong")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["detail"] == unknown_email.json()["detail"]


async def test_login_sets_httponly_cookie(client):
    await register(client)

    resp = await login(client)

    assert resp.status_code == 200
    set_cookie_headers = resp.headers.get_list("set-cookie")
    assert len(set_cookie_headers) == 1
    cookie_header = set_cookie_headers[0]
    assert cookie_header.startswith(f"{settings.COOKIE_NAME}=")

    attributes = [part.strip().lower() for part in cookie_header.split(";")]
    assert "httponly" in attributes
    assert "samesite=lax" in attributes
    assert "secure" not in attributes  # COOKIE_SECURE=false for local http tests

    # The DB stores only the SHA-256 of the cookie token.
    raw_token = resp.cookies[settings.COOKIE_NAME]
    async with AsyncSessionLocal() as db:
        stored = await db.scalar(select(Session.token_hash))
        assert stored is not None
        assert stored != raw_token
        assert stored == hash_session_token(raw_token)


async def test_protected_route_without_cookie_returns_401(client):
    resp = await client.get(ME_URL)

    assert resp.status_code == 401


async def test_expired_session_returns_401(client):
    await register(client)
    token = secrets.token_urlsafe(32)

    async with AsyncSessionLocal() as db:
        user_id = await db.scalar(select(User.id).where(User.email == EMAIL))
        db.add(
            Session(
                token_hash=hash_session_token(token),
                user_id=user_id,
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            )
        )
        await db.commit()

    client.cookies.set(settings.COOKIE_NAME, token)
    resp = await client.get(ME_URL)

    assert resp.status_code == 401


async def test_logout_invalidates_session(client):
    await register(client)
    assert (await login(client)).status_code == 200
    assert (await client.get(ME_URL)).status_code == 200

    old_token = client.cookies[settings.COOKIE_NAME]
    assert (await client.post(LOGOUT_URL)).status_code == 200

    # Replay the old cookie explicitly; the deleted row must reject it.
    client.cookies.set(settings.COOKIE_NAME, old_token)
    resp = await client.get(ME_URL)

    assert resp.status_code == 401
