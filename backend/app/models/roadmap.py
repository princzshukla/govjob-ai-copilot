from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.exam import Base


class SavedRoadmap(Base):
    __tablename__ = "saved_roadmaps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE", name="fk_saved_roadmaps_user_id"),
        nullable=False,
    )
    exam_id: Mapped[str] = mapped_column(String(100), index=True)
    target_weeks: Mapped[int] = mapped_column(Integer)
    roadmap_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        # One saved roadmap per account per exam; regenerating replaces it.
        UniqueConstraint("user_id", "exam_id", name="uq_saved_roadmaps_user_exam"),
    )
