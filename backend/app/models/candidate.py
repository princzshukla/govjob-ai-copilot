# app/models/candidate.py
from datetime import date
from sqlalchemy import String, Date, Integer, Numeric, Boolean, ARRAY, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.exam import Base

class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=True)
    dob: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(20), default="Male")
    category: Mapped[str] = mapped_column(String(20), default="General")  # General, OBC-NCL, SC, ST, EWS
    is_pwd: Mapped[bool] = mapped_column(Boolean, default=False)
    domicile_state: Mapped[str] = mapped_column(String(50), nullable=False)
    
    highest_degree: Mapped[str] = mapped_column(String(100), nullable=False)
    stream: Mapped[str] = mapped_column(String(100), nullable=True)
    percentage_cgpa: Mapped[float] = mapped_column(Numeric(5, 2), nullable=True)
    passing_year: Mapped[int] = mapped_column(Integer, nullable=True)
    
    skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])
    raw_resume_text: Mapped[str] = mapped_column(Text, nullable=True)