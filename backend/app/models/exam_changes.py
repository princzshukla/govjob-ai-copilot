# app/models/exam_changes.py
"""Append-only audit records for the jobs watchdog."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.exam import Base


class ExamNotificationChange(Base):
    __tablename__ = "exam_notification_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("exam_notifications.id", ondelete="CASCADE"), nullable=False,
        index=True,
    )
    field: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_kind: Mapped[str] = mapped_column(String(30), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class JobsWatchdogReport(Base):
    __tablename__ = "jobs_watchdog_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    total_live: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_seeds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    distinct_matched_seeds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unmatched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_candidates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ambiguous: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    newly_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    official_pdfs_verified: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    awaiting_review: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deadlines_approaching: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    coverage_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    honest: Mapped[bool] = mapped_column(default=True, nullable=False)
    payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
