from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.exam import Base


class RoadmapProgress(Base):
    """One row per completed week of a saved roadmap.

    Ownership is derived from ``saved_roadmaps.user_id`` rather than duplicated
    here: a second owner column could drift from the roadmap's real owner. The
    roadmap FK cascades, and the roadmap itself cascades from the user, so
    deleting an account still removes all of its progress.

    The composite primary key makes "mark week done" idempotent at the database
    level: repeating the write cannot create a duplicate row.
    """

    __tablename__ = "roadmap_progress"

    roadmap_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "saved_roadmaps.id",
            ondelete="CASCADE",
            name="fk_roadmap_progress_roadmap_id",
        ),
        primary_key=True,
    )
    week_no: Mapped[int] = mapped_column(Integer, primary_key=True)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("week_no >= 1", name="ck_roadmap_progress_week_positive"),
    )
