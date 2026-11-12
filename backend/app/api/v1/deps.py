from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_session_token
from app.models.auth import Session, User


async def _resolve_user(request: Request, db: AsyncSession) -> User | None:
    """Return the session owner, or None. Never raises for guests."""
    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        return None

    # Look up by hash only: the raw token never touches the database.
    result = await db.execute(
        select(Session).where(Session.token_hash == hash_session_token(token))
    )
    session = result.scalar_one_or_none()

    # Expired or unknown sessions are both treated as logged out.
    if session is None or session.expires_at <= datetime.now(timezone.utc):
        return None

    return await db.get(User, session.user_id)


async def current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Resolve the logged-in user from the session cookie, or 401."""
    user = await _resolve_user(request, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    request.state.user_id = user.id
    return user


async def optional_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User | None:
    """Same as current_user, but a missing/expired session is just a guest."""
    user = await _resolve_user(request, db)
    if user is not None:
        request.state.user_id = user.id
    return user


def user_or_ip_key(request: Request) -> str:
    """Rate-limit key: the account when logged in, otherwise the client IP.

    current_user/optional_current_user run as dependencies before the endpoint
    (and therefore before slowapi's check), so state.user_id is already set.
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id is not None:
        return f"user:{user_id}"
    return f"ip:{get_remote_address(request)}"
