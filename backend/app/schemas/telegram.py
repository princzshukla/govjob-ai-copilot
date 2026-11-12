from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TelegramLinkStartResponse(BaseModel):
    """One-time code the user sends to the bot to prove chat ownership."""

    code: str
    expires_at: datetime
    bot_username: str


class TelegramLinkStatusResponse(BaseModel):
    linked: bool
    # Masked so the API never exposes the full chat id.
    chat_id: Optional[str] = None
    verified_at: Optional[datetime] = None


class AlertRequest(BaseModel):
    """Deadline alert payload.

    There is intentionally no ``chat_id``: the destination is the verified chat
    stored for the session user.
    """

    exam_title: str = Field(min_length=1, max_length=255)
    application_deadline: str = Field(min_length=1, max_length=32)
    days_left: int = Field(ge=-3650, le=3650)


class TelegramChat(BaseModel):
    id: int


class TelegramMessage(BaseModel):
    chat: TelegramChat
    text: Optional[str] = None


class TelegramUpdate(BaseModel):
    """Subset of a Telegram update; unknown fields are ignored."""

    message: Optional[TelegramMessage] = None
