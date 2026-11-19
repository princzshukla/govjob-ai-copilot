# app/models/exam.py
from datetime import date
from typing import Optional

from sqlalchemy import ARRAY, Boolean, Date, Integer, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ExamNotification(Base):
    __tablename__ = "exam_notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    organizing_body: Mapped[str] = mapped_column(String(100), nullable=False)
    post_type: Mapped[str] = mapped_column(String(50), default="General")

    notification_date: Mapped[date] = mapped_column(Date, nullable=True)
    application_deadline: Mapped[date] = mapped_column(Date, nullable=False)
    exam_date: Mapped[date] = mapped_column(Date, nullable=True)
    # Official application-window opening date. NULL when the notice does not
    # state one — never inferred from the aggregator.
    application_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # True once the jobs watchdog has confirmed the window against the
    # official PDF. The startup seed upsert then leaves deadline fields alone.
    deadline_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    official_pdf_url: Mapped[str] = mapped_column(Text, nullable=True)

    # Statutory Eligibility Constraints
    min_age: Mapped[int] = mapped_column(Integer, nullable=False)
    max_age_general: Mapped[int] = mapped_column(Integer, nullable=False)
    age_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Qualification Constraints
    allowed_degrees: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    allowed_streams: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)
    min_percentage: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)

    # Syllabus Topics for Plan-B Overlap & AI Roadmaps
    topics: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=list, nullable=True)

    # Domicile Constraints (Null = Pan-India Central Vacancy)
    state_restriction: Mapped[str] = mapped_column(String(50), nullable=True)

    # T7: tri-state because many notifications do not mention final-year students.
    # True = allowed, False = not allowed, None = engine must ask for manual check.
    allows_final_year: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    max_attempts: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Provenance shown on every exam/job result.
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Where the candidate actually applies (official online portal/form).
    # NULL = unknown; the UI shows only the notification PDF as a link.
    apply_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_checked_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Verification of the notification's application window. Stamped when a
    # human or automated check confirms the deadline against an official
    # source ("verified"); NULL/"check_required" means unconfirmed — the UI
    # shows "check official notification" instead of trusting the date.
    verified_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    verification_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)