"""Custom Google sign-in: OIDC authorization code flow with PKCE.

No third-party auth service. Google only supplies an identity assertion (the
ID token); our backend still owns sessions, cookies and user records.

The short-lived state / nonce / PKCE verifier travel in a signed cookie so no
new database table or Redis key is needed, and a callback can only be completed
by the browser that started the flow.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from urllib.parse import urlencode

import httpx
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import urllib3 as google_urllib3
from google.oauth2 import id_token as google_id_token
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from starlette.concurrency import run_in_threadpool

from app.core.config import settings

AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
SCOPES = "openid email profile"
STATE_COOKIE = "oauth_state"
STATE_MAX_AGE = 300  # seconds


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.OAUTH_STATE_SECRET, salt="google-oauth-state")


def make_pkce_verifier() -> str:
    # 64 random bytes -> 86 URL-safe chars (well within RFC 7636's 43–128).
    return secrets.token_urlsafe(64)


def pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def sign_state(payload: dict[str, str]) -> str:
    return _serializer().dumps(payload)


def read_state(value: str | None) -> dict[str, str] | None:
    """Return the signed payload, or None on tampering/expiry/malformation."""
    if not value:
        return None
    try:
        data = _serializer().loads(value, max_age=STATE_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(data, dict):
        return None
    return {key: str(val) for key, val in data.items() if isinstance(val, str)}


def authorization_url(*, state: str, nonce: str, code_challenge: str) -> str:
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "prompt": "select_account",
        "access_type": "online",
    }
    return f"{AUTHORIZATION_ENDPOINT}?{urlencode(params)}"


def validate_next(value: str | None) -> str:
    """Only accept a single-leading-slash internal path (no scheme, no //)."""
    if not value or not value.startswith("/") or value.startswith("//"):
        return "/"
    if "\\" in value or any(ord(ch) < 32 for ch in value):
        return "/"
    return value


async def exchange_code(code: str, code_verifier: str) -> str:
    """Swap the one-time authorization code for Google's ID token."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            },
        )
    if response.status_code != 200:
        raise ValueError("Token exchange failed")
    token = response.json().get("id_token")
    if not isinstance(token, str) or not token:
        raise ValueError("Missing ID token")
    return token


def _verify_sync(id_token_value: str) -> dict:
    # google-auth verifies the RS256 signature against Google's cached JWKS,
    # plus iss, aud and exp. Blocking IO: called via run_in_threadpool.
    return dict(google_id_token.verify_oauth2_token(
        id_token_value, google_urllib3.Request(), settings.GOOGLE_CLIENT_ID
    ))


async def verify_id_token(id_token_value: str, *, nonce: str) -> dict:
    """Verify the assertion and the application-level checks we rely on."""
    info = await run_in_threadpool(_verify_sync, id_token_value)
    if info.get("nonce") != nonce:
        raise ValueError("Invalid nonce")
    if info.get("email_verified") is not True:
        raise ValueError("Email not verified")
    sub = info.get("sub")
    email = info.get("email")
    if not isinstance(sub, str) or not sub or not isinstance(email, str) or not email:
        raise ValueError("Missing identity claims")
    return info


# Exported for the exception handler in the endpoint.
GOOGLE_ERRORS = (ValueError, httpx.HTTPError, GoogleAuthError)
