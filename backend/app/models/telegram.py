from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
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
