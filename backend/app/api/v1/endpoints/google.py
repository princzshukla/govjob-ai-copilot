"""Google sign-in endpoints: /auth/google/start and /auth/google/callback.

The callback issues the SAME session cookie as password login, so the rest of
the app (including /auth/me and the 401 handler) needs no changes.
"""

from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.cookies import set_session_cookie
from app.api.v1.deps import user_or_ip_key
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import generate_session_token, hash_session_token
from app.models.auth import Session, User
from app.services import google_oauth as google

router = APIRouter(prefix="/auth/google", tags=["Auth"])

_FRONTEND = settings.FRONTEND_URL.rstrip("/")


def _require_enabled() -> None:
    if not settings.GOOGLE_AUTH_ENABLED:
        raise HTTPException(status_code=404, detail="Not found")


def _redirect(error: str | None = None, target: str | None = None) -> RedirectResponse:
    """Never put a code/token in the final URL — only a short error marker."""
    if error:
        return RedirectResponse(f"{_FRONTEND}/?auth_error={error}", status_code=302)
    return RedirectResponse(target or _FRONTEND, status_code=302)


@router.get("/start")
@limiter.limit("10/minute", key_func=user_or_ip_key)
async def start(
    request: Request,
    next: str = Query("/"),
) -> RedirectResponse:
    _require_enabled()
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = google.make_pkce_verifier()

    response = RedirectResponse(
        google.authorization_url(
            state=state,
            nonce=nonce,
            code_challenge=google.pkce_challenge(verifier),
        ),
        status_code=302,
    )
    response.set_cookie(
        google.STATE_COOKIE,
        google.sign_state(
            {"state": state, "nonce": nonce, "verifier": verifier, "next": google.validate_next(next)}
        ),
        max_age=google.STATE_MAX_AGE,
        path="/",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )
    return response


def _verification_error(exc: Exception) -> str:
    message = str(exc).lower()
    if "nonce" in message:
        return "bad_nonce"
    if "verified" in message:
        return "unverified_email"
    return "google_verification_failed"


@router.get("/callback")
@limiter.limit("10/minute", key_func=user_or_ip_key)
async def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    _require_enabled()
    if error:
        return _redirect(error="google_cancelled")
    if not code or not state:
        return _redirect(error="google_invalid_request")

    flow = google.read_state(request.cookies.get(google.STATE_COOKIE))
    if flow is None:
        return _redirect(error="expired_state")
    if not secrets.compare_digest(flow.get("state", ""), state):
        return _redirect(error="state_mismatch")

    try:
        id_token = await google.exchange_code(code, flow.get("verifier", ""))
        info = await google.verify_id_token(id_token, nonce=flow.get("nonce", ""))
    except google.GOOGLE_ERRORS as exc:
        return _redirect(error=_verification_error(exc))

    sub = info["sub"]
    email = info["email"].strip().lower()

    user = await db.scalar(select(User).where(User.google_sub == sub))
    first_login = user is None
    if user is None:
        # Do NOT auto-link by email: an account with this address may belong to
        # a password user. Linking is an explicit, signed-in action for later.
        existing = await db.scalar(select(User).where(User.email == email))
        if existing is not None:
            return _redirect(error="account_exists")
        user = User(
            email=email,
            full_name=(str(info.get("name") or "").strip()[:120] or None),
            phone=None,
            password_hash=None,  # Google-only: distinguishable in the UI/API
            google_sub=sub,
            email_verified_at=datetime.now(timezone.utc),
        )
        db.add(user)
        try:
            await db.commit()
            await db.refresh(user)
        except IntegrityError:
            # Concurrent registration with the same email or sub.
            await db.rollback()
            return _redirect(error="account_exists")
    else:
        # Google is the source of truth for identity claims. A user can change
        # their primary email/name in Google; keep our copy current without
        # ever adopting an email that already belongs to another account.
        name = str(info.get("name") or "").strip()[:120] or None
        changed = False
        if user.email != email:
            clash = await db.scalar(
                select(User.id).where(User.email == email, User.id != user.id)
            )
            if clash is None:
                user.email = email
                changed = True
        if user.full_name != name:
            user.full_name = name
            changed = True
        if changed:
            try:
                await db.commit()
            except IntegrityError:
                # Concurrent change claimed the email — keep the old, valid data.
                await db.rollback()

    token = generate_session_token()
    db.add(
        Session(
            token_hash=hash_session_token(token),
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.SESSION_TTL_DAYS),
        )
    )
    await db.commit()

    target = google.validate_next(flow.get("next"))
    # `google=1` tells the SPA to claim any guest draft now that there is an
    # account; `profile=phone` opens the one-time phone step. Both are consumed
    # and removed from the URL by the frontend.
    markers = ["google=1"]
    if first_login and not user.phone:
        markers.append("profile=phone")
    target += ("&" if "?" in target else "?") + "&".join(markers)

    response = _redirect(target=target)
    set_session_cookie(response, token)
    response.delete_cookie(
        google.STATE_COOKIE,
        path="/",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )
    return response
