from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.exam import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Stored trimmed and lowercased; unique constraint is the race-safe guard.
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    # NULL for Google-only accounts — they have no password to verify. Password
    # login handles NULL by verifying against a dummy hash (constant work, same
    # generic 401), so it cannot leak whether an account is federated.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Google's `sub` claim: the stable, never-reused account identifier. Email
    # is NOT safe as an identity key (it can change), so this is the link.
    google_sub: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )
    # Optional until Phase 3 makes full_name mandatory at registration.
    full_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # E.164 normalized in Phase 3; nullable because phone is optional.
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    phone_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        # Explicit names so autogenerate/downgrade can reference the constraints.
        UniqueConstraint("phone", name="uq_users_phone"),
        UniqueConstraint("google_sub", name="uq_users_google_sub"),
    )

    @property
    def has_password(self) -> bool:
        """False for Google-only accounts (used by the UI and the API)."""
        return self.password_hash is not None


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Only the SHA-256 hex digest of the cookie token is stored, never the token.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_sessions_token_hash", "token_hash", unique=True),
        Index("ix_sessions_expires_at", "expires_at"),
    )
