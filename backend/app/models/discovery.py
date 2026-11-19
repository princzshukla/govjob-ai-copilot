# app/models/discovery.py
"""Discovery queue for unmatched aggregator notifications.

This is a *research* queue, not a second ingestion pipeline. Rows are created
from the coverage watchdog's unmatched entries; official URLs and PDF evidence
are attached by the discovery engine, and humans decide what gets promoted
into the existing SEED_ADMIT_CARDS / admit_cards architecture.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.exam import Base


class NotificationDiscovery(Base):
    __tablename__ = "notification_discovery_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    aggregator_title: Mapped[str] = mapped_column(String(500), nullable=False)
    aggregator_url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    organization: Mapped[str | None] = mapped_column(String(120), nullable=True)
    recruitment_year: Mapped[str | None] = mapped_column(String(4), nullable=True)
    notice_subtype: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # 'job' (jobs watchdog) or 'admit_card' (legacy admit-card watchdog).
    notification_kind: Mapped[str] = mapped_column(
        String(20), nullable=False, default="admit_card",
        server_default="admit_card"
    )
    # new_recruitment | duplicate | ambiguous | irrelevant | requires_official_verification
    classification: Mapped[str | None] = mapped_column(String(30), nullable=True)
    official_website: Mapped[str | None] = mapped_column(Text, nullable=True)
    official_notification_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    official_pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_information: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    confidence_score: Mapped[float] = mapped_column(default=0.0, nullable=False, server_default="0")
    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="unverified", server_default="unverified"
    )
    discovery_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="discovered", server_default="discovered"
    )
    duplicate_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Explicit names match the migrations exactly; `index=True` would generate
    # `ix_notification_discovery_queue_*` and fail `alembic check`.
    __table_args__ = (
        Index("ix_notification_discovery_kind", "notification_kind"),
        Index("ix_notification_discovery_status", "discovery_status"),
    )


class DiscoveryHistory(Base):
    """Append-only audit trail for verification/approval decisions."""

    __tablename__ = "discovery_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    discovery_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("notification_discovery_queue.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    actor: Mapped[str] = mapped_column(String(120), nullable=False, default="system", server_default="system")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
