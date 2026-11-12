import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.api.v1.cookies import clear_session_cookie
from app.api.v1.deps import current_user, user_or_ip_key
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import hash_password, verify_password
from app.models.auth import Session, User
from app.schemas.auth import ChangePasswordIn, DeleteAccountIn, UserOut, UserUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])

# Same generic wording for every bad password: an attacker must not be able to
# tell a wrong password from a missing account field.
INVALID_PASSWORD = "Invalid password"


@router.patch("/me", response_model=UserOut)
async def update_me(
    payload: UserUpdate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """Edit the signed-in user's display name.

    ``email`` and ``phone`` are deliberately absent from ``UserUpdate``, which
    also forbids extra fields, so a client cannot smuggle them into this
    request; they are silently untouched regardless.
    """
    user.full_name = payload.full_name
    await db.commit()
    return UserOut.model_validate(user)


@router.post("/me/change-password", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute", key_func=user_or_ip_key)
async def change_password(
    request: Request,
    payload: ChangePasswordIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    if not await run_in_threadpool(
        verify_password, user.password_hash, payload.current_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_PASSWORD
        )

    # Argon2 is CPU-bound; hash off the event loop, as login does.
    user.password_hash = await run_in_threadpool(hash_password, payload.new_password)

    # Revoke every other session for this account: a stolen cookie must stop
    # working as soon as the password changes. The current session survives.
    session_id: int = request.state.session_id
    await db.execute(
        delete(Session).where(
            Session.user_id == user.id,
            Session.id != session_id,
        )
    )
    await db.commit()

    logger.info("Password changed for user_id=%s", user.id)
    return {"message": "Password changed"}


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute", key_func=user_or_ip_key)
async def delete_me(
    request: Request,
    payload: DeleteAccountIn,
    response: Response,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    if not await run_in_threadpool(verify_password, user.password_hash, payload.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_PASSWORD
        )

    # No paid-subscription table exists yet. When one lands, block deletion of
    # an active subscription here (and keep payment/invoice rows for legal
    # retention rather than cascading them away).
    user_id = user.id
    await db.delete(user)
    await db.commit()

    clear_session_cookie(response)
    logger.info("Account deleted for user_id=%s", user_id)
