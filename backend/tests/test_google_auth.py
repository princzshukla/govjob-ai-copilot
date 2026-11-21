"""Custom Google sign-in: authorization code + PKCE, no third-party auth service."""

from urllib.parse import parse_qs, urlparse

import pytest

from app.core.config import settings
from app.services import google_oauth as google

CLIENT_ID = "test-client.apps.googleusercontent.com"
# Capture once: patch_google is called multiple times in one test and must not
# wrap a previously patched wrapper.
REAL_VERIFY_ID_TOKEN = google.verify_id_token


@pytest.fixture(autouse=True)
def google_settings(monkeypatch):
    # Settings is a singleton; mutating it here is what the endpoints read at
    # request time (validation at import time still uses the real env).
    monkeypatch.setattr(settings, "GOOGLE_AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", CLIENT_ID)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setattr(settings, "GOOGLE_REDIRECT_URI", "http://testserver/api/v1/auth/google/callback")
    monkeypatch.setattr(settings, "OAUTH_STATE_SECRET", "test-state-secret")


def token_info(*, sub="google-sub-1", email="google@example.com", name="Google User", verified=True):
    return {"sub": sub, "email": email, "name": name, "email_verified": verified}


def patch_google(monkeypatch, info=None, error=None):
    async def exchange(code, verifier):
        return "fake-id-token"

    async def verify(token, *, nonce):
        # Stub only the network/JWKS step, then run the real verification so
        # nonce, email_verified and identity-claim checks are still exercised.
        def fake_verify_sync(_token):
            if error is not None:
                raise error
            payload = dict(info or token_info())
            payload.setdefault("nonce", nonce)
            return payload

        monkeypatch.setattr(google, "_verify_sync", fake_verify_sync)
        return await REAL_VERIFY_ID_TOKEN(token, nonce=nonce)

    monkeypatch.setattr(google, "exchange_code", exchange)
    monkeypatch.setattr(google, "verify_id_token", verify)


async def start_flow(client, next_path="/"):
    res = await client.get(
        "/api/v1/auth/google/start", params={"next": next_path}, follow_redirects=False
    )
    assert res.status_code == 302
    cookie = res.cookies.get(google.STATE_COOKIE)
    assert cookie
    return cookie, google.read_state(cookie)


async def callback(client, cookie, flow, **overrides):
    params = {"code": "the-code", "state": flow["state"]}
    params.update(overrides)
    return await client.get(
        "/api/v1/auth/google/callback",
        params=params,
        cookies={google.STATE_COOKIE: cookie},
        follow_redirects=False,
    )


def error_of(response) -> str | None:
    query = parse_qs(urlparse(response.headers.get("location", "")).query)
    return (query.get("auth_error") or [None])[0]


# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_start_builds_pkce_url_and_signed_cookie(client):
    res = await client.get(
        "/api/v1/auth/google/start", params={"next": "/?tab=roadmap"}, follow_redirects=False
    )
    cookie = res.cookies.get(google.STATE_COOKIE)
    flow = google.read_state(cookie)
    location = urlparse(res.headers["location"])
    params = parse_qs(location.query)
    assert location.netloc == "accounts.google.com"
    assert params["client_id"] == [CLIENT_ID]
    assert params["response_type"] == ["code"]
    assert params["scope"] == ["openid email profile"]
    assert params["code_challenge_method"] == ["S256"]
    assert params["state"]
    assert "nonce" in params and "code_challenge" in params
    assert flow["next"] == "/?tab=roadmap"
    assert google.pkce_challenge(flow["verifier"]) == params["code_challenge"][0]


@pytest.mark.asyncio
async def test_state_mismatch_is_rejected(client, monkeypatch):
    patch_google(monkeypatch)
    cookie, flow = await start_flow(client)
    res = await callback(client, cookie, flow, state="attacker-state")
    assert error_of(res) == "state_mismatch"
    assert "session_id" not in res.cookies


@pytest.mark.asyncio
async def test_expired_state_cookie_is_rejected(client, monkeypatch):
    patch_google(monkeypatch)
    cookie, flow = await start_flow(client)
    monkeypatch.setattr(google, "STATE_MAX_AGE", -1)  # every token is now "expired"
    res = await callback(client, cookie, flow)
    assert error_of(res) == "expired_state"
    assert "session_id" not in res.cookies


@pytest.mark.asyncio
async def test_bad_nonce_is_rejected(client, monkeypatch):
    patch_google(monkeypatch, error=ValueError("Invalid nonce"))
    cookie, flow = await start_flow(client)
    res = await callback(client, cookie, flow)
    assert error_of(res) == "bad_nonce"
    assert "session_id" not in res.cookies


@pytest.mark.asyncio
async def test_unverified_email_is_rejected(client, monkeypatch):
    patch_google(monkeypatch, info=token_info(verified=False))
    cookie, flow = await start_flow(client)
    res = await callback(client, cookie, flow)
    assert error_of(res) == "unverified_email"
    assert "session_id" not in res.cookies


@pytest.mark.asyncio
async def test_google_email_matching_existing_password_account_is_refused(client, monkeypatch):
    registered = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "google@example.com",
            "password": "password123",
            "full_name": "Legacy User",
        },
    )
    assert registered.status_code == 201
    patch_google(monkeypatch, info=token_info(email="google@example.com"))
    cookie, flow = await start_flow(client)
    res = await callback(client, cookie, flow)
    assert error_of(res) == "account_exists"
    assert "session_id" not in res.cookies


@pytest.mark.asyncio
async def test_new_google_user_gets_session_and_profile_step(client, monkeypatch):
    patch_google(monkeypatch)
    cookie, flow = await start_flow(client, "/?tab=jobs")
    res = await callback(client, cookie, flow)
    assert res.status_code == 302
    assert urlparse(res.headers["location"]).path == "/"
    query = parse_qs(urlparse(res.headers["location"]).query)
    assert query["google"] == ["1"]
    assert query["profile"] == ["phone"]
    assert "session_id" in res.cookies
    # httpx drops expired cookies from Response.cookies, so assert on the
    # raw Set-Cookie header instead.
    set_cookies = res.headers.get_list("set-cookie")
    assert any(
        cookie.startswith(f"{google.STATE_COOKIE}=") and "max-age=0" in cookie.lower()
        for cookie in set_cookies
    )

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "google@example.com"
    assert body["phone"] is None
    assert body["has_password"] is False


@pytest.mark.asyncio
async def test_returning_google_user_gets_fresh_claims(client, monkeypatch):
    patch_google(monkeypatch, info=token_info(email="old@example.com", name="Old Name"))
    cookie, flow = await start_flow(client)
    assert error_of(await callback(client, cookie, flow)) is None

    patch_google(monkeypatch, info=token_info(email="new@example.com", name="New Name"))
    cookie, flow = await start_flow(client)
    assert error_of(await callback(client, cookie, flow)) is None

    me = (await client.get("/api/v1/auth/me")).json()
    assert me["email"] == "new@example.com"
    assert me["full_name"] == "New Name"


@pytest.mark.asyncio
async def test_duplicate_phone_returns_409(client):
    first = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@example.com",
            "password": "password123",
            "full_name": "Owner",
            "phone": "9876543210",
        },
    )
    assert first.status_code == 201
    await client.post(
        "/api/v1/auth/logout",
    )
    second = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "other@example.com",
            "password": "password123",
            "full_name": "Other",
        },
    )
    assert second.status_code == 201
    phone = await client.patch("/api/v1/users/me/phone", json={"phone": "9876543210"})
    assert phone.status_code == 409


@pytest.mark.asyncio
async def test_password_login_with_null_hash_is_generic_401(client, monkeypatch):
    patch_google(monkeypatch)
    cookie, flow = await start_flow(client)
    assert (await callback(client, cookie, flow)).status_code == 302

    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "google@example.com", "password": "anything123"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_phone_completion_and_no_password_change(client, monkeypatch):
    patch_google(monkeypatch)
    cookie, flow = await start_flow(client)
    await callback(client, cookie, flow)

    phone = await client.patch("/api/v1/users/me/phone", json={"phone": "9876543210"})
    assert phone.status_code == 200
    assert phone.json()["phone"] == "+919876543210"

    change = await client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "x", "new_password": "newpassword1"},
    )
    assert change.status_code == 400
    assert "no password" in change.json()["detail"].lower()


@pytest.mark.asyncio
async def test_deleting_account_frees_google_sub_for_reuse(client, monkeypatch):
    patch_google(monkeypatch)
    cookie, flow = await start_flow(client)
    await callback(client, cookie, flow)
    first_id = (await client.get("/api/v1/auth/me")).json()["id"]

    deleted = await client.request("DELETE", "/api/v1/users/me", json={"password": ""})
    assert deleted.status_code == 204

    cookie, flow = await start_flow(client)
    res = await callback(client, cookie, flow)
    assert error_of(res) is None
    assert (await client.get("/api/v1/auth/me")).json()["id"] != first_id


@pytest.mark.asyncio
async def test_providers_endpoint_reflects_flag(client, monkeypatch):
    res = await client.get("/api/v1/auth/providers")
    assert res.status_code == 200
    assert res.json() == {"password": True, "google": True}
    monkeypatch.setattr(settings, "GOOGLE_AUTH_ENABLED", False)
    assert (await client.get("/api/v1/auth/providers")).json()["google"] is False


@pytest.mark.asyncio
async def test_disabled_google_flow_returns_404(client, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_AUTH_ENABLED", False)
    assert (await client.get("/api/v1/auth/google/start", follow_redirects=False)).status_code == 404


@pytest.mark.asyncio
async def test_real_verification_constructs_transport(monkeypatch):
    # The endpoint stubs _verify_sync, so without this test the real transport
    # construction is never exercised (Request() used to raise TypeError).
    captured = {}

    def fake_verify(token, request, audience):
        captured["request"] = request
        captured["audience"] = audience
        return {
            "sub": "google-sub-1",
            "email": "google@example.com",
            "name": "Google User",
            "email_verified": True,
            "nonce": "n",
        }

    monkeypatch.setattr(google.google_id_token, "verify_oauth2_token", fake_verify)
    info = await google.verify_id_token("fake-id-token", nonce="n")
    assert info["sub"] == "google-sub-1"
    assert captured["request"] is not None
    assert captured["audience"] == settings.GOOGLE_CLIENT_ID


@pytest.mark.parametrize(
    "value,expected",
    [
        ("/", "/"),
        ("/?tab=jobs", "/?tab=jobs"),
        ("//evil.com", "/"),
        ("https://evil.com", "/"),
        ("/\\evil.com", "/"),
        ("/?tab=jobs#results", "/?tab=jobs"),  # fragment would eat our markers
        (None, "/"),
        ("", "/"),
    ],
)
def test_validate_next_never_allows_open_redirect(value, expected):
    assert google.validate_next(value) == expected
