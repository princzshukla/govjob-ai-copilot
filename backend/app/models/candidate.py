# app/models/candidate.py
from datetime import date
from sqlalchemy import (
    ARRAY,
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.models.exam import Base

class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # One profile per account. Guests cannot persist a profile (Phase 4 adds
    # the draft-claim flow), so the owner is always known here.
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "users.id", ondelete="CASCADE", name="fk_candidate_profiles_user_id"
        ),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(120), nullable=True)
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str] = mapped_column(String(20), default="Male")
    category: Mapped[str] = mapped_column(String(20), default="General")  # General, OBC-NCL, SC, ST, EWS
    is_pwd: Mapped[bool] = mapped_column(Boolean, default=False)
    domicile_state: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    highest_degree: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stream: Mapped[str] = mapped_column(String(100), nullable=True)
    percentage_cgpa: Mapped[float] = mapped_column(Numeric(5, 2), nullable=True)
    passing_year: Mapped[int] = mapped_column(Integer, nullable=True)
    
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])
    raw_resume_text: Mapped[str] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_candidate_profiles_user_id"),
    )
