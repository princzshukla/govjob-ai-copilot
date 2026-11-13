from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.exam import Base


class EligibilityReport(Base):
    """User report that an eligibility result was wrong.

    Contact details (name, raw resume text, email/phone) are deliberately not
    copied into the snapshot. The exam is stored both by id and as a snapshot so
    the report stays meaningful if the notification later changes.
    """

    __tablename__ = "eligibility_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    exam_id: Mapped[str] = mapped_column(String(100), index=True)
    reported_verdict: Mapped[str] = mapped_column(String(20), nullable=True)
    expected_verdict: Mapped[str] = mapped_column(String(20), nullable=True)
    candidate_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    exam_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
