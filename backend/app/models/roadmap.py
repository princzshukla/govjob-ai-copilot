from datetime import datetime
from sqlalchemy import String, Integer, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.models.exam import Base

class SavedRoadmap(Base):
    __tablename__ = "saved_roadmaps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    exam_id: Mapped[str] = mapped_column(String(100), index=True)
    target_weeks: Mapped[int] = mapped_column(Integer)
    roadmap_json: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)