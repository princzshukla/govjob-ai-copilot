"""Session-cookie helpers shared by the auth and account endpoints.

Keeping the attributes in one place means login, logout, and account deletion
can never drift apart (for example, clearing a cookie without ``samesite`` or
``secure`` leaves the browser holding a stale session).
"""

from fastapi import Response

from app.core.config import settings

# 7 days, expressed in seconds for the cookie's max-age.
_SESSION_MAX_AGE = settings.SESSION_TTL_DAYS * 24 * 60 * 60


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        max_age=_SESSION_MAX_AGE,
        path="/",
        httponly=True,  # JS cannot read it, so XSS can't exfiltrate the session
        secure=settings.COOKIE_SECURE,  # must be true in production (HTTPS)
        samesite="lax",  # blocks cross-site POST (CSRF), allows normal navigation
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
    )
