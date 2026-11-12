# app/models/exam.py
from datetime import date
from sqlalchemy import ARRAY, Boolean, Date, Integer, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ExamNotification(Base):
    __tablename__ = "exam_notifications"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    organizing_body: Mapped[str] = mapped_column(String(100), nullable=False)
    post_type: Mapped[str] = mapped_column(String(50), default="General")

    notification_date: Mapped[date] = mapped_column(Date, nullable=True)
    application_deadline: Mapped[date] = mapped_column(Date, nullable=False)
    exam_date: Mapped[date] = mapped_column(Date, nullable=True)
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
    topics: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # Domicile Constraints (Null = Pan-India Central Vacancy)
    state_restriction: Mapped[str] = mapped_column(String(50), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)