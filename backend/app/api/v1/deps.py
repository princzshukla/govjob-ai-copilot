from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_session_token
from app.models.auth import Session, User


async def current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Resolve the logged-in user from the session cookie, or 401."""
    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    # Look up by hash only: the raw token never touches the database.
    result = await db.execute(
        select(Session).where(Session.token_hash == hash_session_token(token))
    )
    session = result.scalar_one_or_none()

    # Expired or unknown sessions are both treated as logged out.
    if session is None or session.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    user = await db.get(User, session.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return user
