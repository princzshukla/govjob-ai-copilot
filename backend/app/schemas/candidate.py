# app/schemas/candidate.py
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class ParsedResumeProfile(BaseModel):
    """Schema used by the LLM to extract ONLY what is explicitly present in the resume."""
    full_name: Optional[str] = None
    dob: Optional[date] = Field(
        default=None,
        description="YYYY-MM-DD if explicitly written in resume, else null",
    )
    gender: Optional[str] = Field(
        default=None,
        description="Male, Female, Other if explicitly written, else null",
    )
    category: Optional[str] = Field(
        default=None,
        description="General, OBC-NCL, SC, ST, EWS if explicitly written, else null",
    )
    is_pwd: Optional[bool] = Field(
        default=None,
        description="True/False if PwD status mentioned, else null",
    )
    domicile_state: Optional[str] = Field(
        default=None,
        description="Indian State if address/location is clear, else null",
    )
    highest_degree: Optional[str] = Field(
        default=None,
        description="e.g., B.Tech, BCA, B.Sc, B.Com, BA, 12th, else null",
    )
    stream: Optional[str] = Field(
        default=None,
        description="e.g., Computer Science, Mechanical, Accounts, else null",
    )
    percentage_cgpa: Optional[float] = Field(
        default=None,
        description="Graduation percentage or CGPA if written, else null",
    )
    passing_year: Optional[int] = Field(
        default=None,
        description="Graduation passing year if written, else null",
    )
    skills: List[str] = Field(default_factory=list)

    @field_validator("skills", mode="before")
    @classmethod
    def ensure_skills_list(cls, v):
        return v if isinstance(v, list) else []


class MissingFieldPrompt(BaseModel):
    field_name: str
    label: str
    question: str
    input_type: str  # "date", "select", "text", "number"
    options: Optional[List[str]] = None


class ResumeParseResponse(BaseModel):
    extracted_profile: ParsedResumeProfile
    is_complete_for_gov_jobs: bool
    missing_fields: List[MissingFieldPrompt]
    message: str


class CandidateProfileCreate(BaseModel):
    """Strict schema required for final government job eligibility evaluation."""
    full_name: Optional[str] = None
    dob: date = Field(..., description="Required Date of birth in YYYY-MM-DD")
    gender: str = Field(default="Male")
    category: str = Field(..., description="Required: General, OBC-NCL, SC, ST, EWS")
    is_pwd: bool = Field(default=False)
    domicile_state: str = Field(..., description="Required: State of domicile")
    highest_degree: str = Field(
        ..., description="Required: B.Tech, BCA, B.Sc, B.Com, BA, 12th"
    )
    stream: Optional[str] = Field(default="Any")
    percentage_cgpa: float = Field(
        ..., description="Required: Aggregate percentage (e.g., 65.5)"
    )
    passing_year: Optional[int] = None
    # "Completed" or "Final Year / Appearing". Defaults keep older clients working.
    graduation_status: str = Field(default="Completed")
    # Attempts already taken. The current attempt is not included.
    previous_attempts: int = Field(default=0, ge=0)
    skills: List[str] = Field(default_factory=list)
    raw_resume_text: Optional[str] = None

    @field_validator("skills", mode="before")
    @classmethod
    def ensure_create_skills_list(cls, v):
        return v if isinstance(v, list) else []


class CandidateProfileResponse(CandidateProfileCreate):
    profile_id: str