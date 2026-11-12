from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.exam import Base


class TelegramLink(Base):
    """Verified Telegram chat linked to an account.

    Alerts may only be sent to the chat stored here, never to a ``chat_id``
    supplied by the client.
    """

    __tablename__ = "telegram_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE", name="fk_telegram_links_user_id"),
        nullable=False,
    )
    chat_id: Mapped[str] = mapped_column(String(64), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        # One link per account, and one account per chat: both directions are
        # unique so a chat cannot be claimed twice.
        UniqueConstraint("user_id", name="uq_telegram_links_user_id"),
        UniqueConstraint("chat_id", name="uq_telegram_links_chat_id"),
    )


class TelegramLinkCode(Base):
    """Short-lived, single-use code the user sends to the bot to prove chat ownership.

    Only the SHA-256 digest of the code is stored. The plaintext exists only in
    the authenticated response that created it, so a database leak cannot be
    replayed to claim an account's Telegram link.
    """

    __tablename__ = "telegram_link_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "users.id", ondelete="CASCADE", name="fk_telegram_link_codes_user_id"
        ),
        nullable=False,
    )
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        # One outstanding code per account: requesting a new code replaces the
        # old one instead of leaving several valid codes around.
        UniqueConstraint("user_id", name="uq_telegram_link_codes_user_id"),
        UniqueConstraint("code_hash", name="uq_telegram_link_codes_code_hash"),
    )
