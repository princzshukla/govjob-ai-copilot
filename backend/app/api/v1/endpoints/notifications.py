import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import current_user, user_or_ip_key
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.auth import User
from app.models.telegram import TelegramLink, TelegramLinkCode
from app.schemas.telegram import (
    AlertRequest,
    TelegramLinkStartResponse,
    TelegramLinkStatusResponse,
    TelegramUpdate,
)
from app.services.notifier import send_telegram_alert

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])

# Header Telegram sets on every webhook call; its value must match the secret
# registered with setWebhook.
WEBHOOK_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _mask_chat_id(chat_id: str) -> str:
    return f"****{chat_id[-4:]}" if len(chat_id) > 4 else "****"


def _extract_code(text: str) -> str | None:
    """Accept both ``/start CODE`` and a bare ``CODE`` message."""
    parts = text.strip().split()
    if not parts:
        return None
    candidate = parts[-1] if parts[0].lower().startswith("/start") else parts[0]
    if not candidate.isalnum() or not 4 <= len(candidate) <= 32:
        return None
    return candidate.upper()


@router.post("/telegram/link", response_model=TelegramLinkStartResponse)
@limiter.limit("10/hour", key_func=user_or_ip_key)
async def start_telegram_link(
    request: Request,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a short-lived code the user sends to the bot.

    The code is only ever returned to the authenticated owner; the database
    stores its SHA-256 digest.
    """
    code = secrets.token_hex(6).upper()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.TELEGRAM_LINK_CODE_TTL_MINUTES
    )

    existing = await db.scalar(
        select(TelegramLinkCode).where(TelegramLinkCode.user_id == user.id)
    )
    if existing is not None:
        existing.code_hash = _hash_code(code)
        existing.expires_at = expires_at
        existing.used_at = None
    else:
        db.add(
            TelegramLinkCode(
                user_id=user.id,
                code_hash=_hash_code(code),
                expires_at=expires_at,
            )
        )
    await db.commit()

    return TelegramLinkStartResponse(
        code=code,
        expires_at=expires_at,
        bot_username=settings.TELEGRAM_BOT_USERNAME,
    )


@router.get("/telegram/status", response_model=TelegramLinkStatusResponse)
@limiter.limit("120/hour", key_func=user_or_ip_key)
async def get_telegram_status(
    request: Request,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    link = await db.scalar(select(TelegramLink).where(TelegramLink.user_id == user.id))
    if link is None:
        return TelegramLinkStatusResponse(linked=False)
    return TelegramLinkStatusResponse(
        linked=True,
        chat_id=_mask_chat_id(link.chat_id),
        verified_at=link.verified_at,
    )


@router.delete("/telegram/link")
@limiter.limit("10/hour", key_func=user_or_ip_key)
async def unlink_telegram(
    request: Request,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(delete(TelegramLink).where(TelegramLink.user_id == user.id))
    await db.execute(delete(TelegramLinkCode).where(TelegramLinkCode.user_id == user.id))
    await db.commit()
    return {"status": "success"}


@router.post("/telegram/webhook")
@limiter.limit("120/minute")
async def telegram_webhook(
    request: Request,
    update: TelegramUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Telegram callback that turns a one-time code into a verified link.

    Fail closed: without a configured secret, or with a mismatched header,
    every call is rejected. Unknown, expired and already-used codes are ignored
    silently (200) so Telegram does not retry them forever.
    """
    expected = settings.TELEGRAM_WEBHOOK_SECRET
    provided = request.headers.get(WEBHOOK_SECRET_HEADER, "")
    if not expected or not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook secret",
        )

    if update.message is None or not update.message.text:
        return {"ok": True}

    code = _extract_code(update.message.text)
    if code is None:
        return {"ok": True}

    link_code = await db.scalar(
        select(TelegramLinkCode).where(TelegramLinkCode.code_hash == _hash_code(code))
    )
    now = datetime.now(timezone.utc)
    if link_code is None or link_code.used_at is not None or link_code.expires_at <= now:
        return {"ok": True}

    chat_id = str(update.message.chat.id)

    # A chat can only belong to one account, and an account to one chat.
    # Removing both sides first makes re-linking idempotent.
    await db.execute(
        delete(TelegramLink).where(
            or_(TelegramLink.user_id == link_code.user_id, TelegramLink.chat_id == chat_id)
        )
    )
    db.add(
        TelegramLink(user_id=link_code.user_id, chat_id=chat_id, verified_at=now)
    )
    link_code.used_at = now
    try:
        await db.commit()
    except IntegrityError:
        # Two updates may race for the same chat; the unique constraints are
        # the source of truth, and Telegram can simply retry.
        await db.rollback()
        logger.warning("Telegram link race for chat %s", chat_id)
        return {"ok": True}

    return {"ok": True}


@router.post("/send-deadline-alert")
@limiter.limit("20/hour", key_func=user_or_ip_key)
async def trigger_deadline_alert(
    request: Request,
    payload: AlertRequest,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a reminder to the session user's verified Telegram chat only."""
    link = await db.scalar(select(TelegramLink).where(TelegramLink.user_id == user.id))
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Link your Telegram account before sending alerts.",
        )

    message = (
        "GovJob Copilot: Deadline Reminder!\n\n"
        f"Exam: {payload.exam_title}\n"
        f"Form deadline: {payload.application_deadline}\n"
        f"Time remaining: {payload.days_left} day(s)\n\n"
        "Open your GovJob Copilot dashboard to apply or review your study roadmap."
    )

    success = await send_telegram_alert(link.chat_id, message)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to dispatch Telegram notification.",
        )

    return {
        "status": "success",
        "message": "Deadline alert sent to your linked Telegram chat.",
    }
