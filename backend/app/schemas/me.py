# app/schemas/me.py
"""Schemas for the session-owned ``/me`` persistence endpoints.

The candidate profile is stored one-row-per-user. Resume parsing can produce
incomplete profiles, so every field except the ones ``candidate_profiles``
requires is optional; payloads are size-capped to keep abuse (and DB overflow)
in check. Clients can never send a percentage or score — progress is computed
server-side.
"""
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.candidate import ParsedResumeProfile
from app.schemas.roadmap import StudyRoadmapResponse

MAX_SKILLS = 50
MAX_SKILL_LEN = 80
MAX_STRING_LEN = 120  # matches the widest column family on candidate_profiles


def _trim_str(value: object) -> object:
    return " ".join(value.split()) if isinstance(value, str) else value


class CandidateProfileIn(ParsedResumeProfile):
    """A (possibly partial) candidate profile saved to the account.

    All fields are optional: a parsed resume yields an incomplete profile, and
    forcing completeness here would block saving a guest's draft to an account.
    Payloads are size-capped below; nested values outside the DB bounds raise a
    validation error instead of a 500.
    """

    model_config = ConfigDict(extra="forbid")

    full_name: Optional[str] = Field(default=None, max_length=MAX_STRING_LEN)
    gender: Optional[str] = Field(default=None, max_length=20)
    category: Optional[str] = Field(default=None, max_length=20)
    domicile_state: Optional[str] = Field(default=None, max_length=50)
    highest_degree: Optional[str] = Field(default=None, max_length=100)
    stream: Optional[str] = Field(default=None, max_length=100)
    passing_year: Optional[int] = Field(default=None, ge=1900, le=2100)

    @field_validator(
        "full_name", "gender", "category", "domicile_state", "highest_degree", "stream",
        mode="before",
    )
    @classmethod
    def trim_strings(cls, value: object) -> object:
        return _trim_str(value)

    @field_validator("skills", mode="before")
    @classmethod
    def cap_skills(cls, value: object) -> object:
        if not isinstance(value, list):
            return []
        trimmed = [v.strip() for v in value if isinstance(v, str) and v.strip()]
        return [v[:MAX_SKILL_LEN] for v in trimmed[:MAX_SKILLS]]

    @field_validator("percentage_cgpa")
    @classmethod
    def percentage_in_range(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not 0 <= value <= 100:
            raise ValueError("percentage_cgpa must be between 0 and 100")
        return value

    def is_empty(self) -> bool:
        return not any(
            [
                self.full_name,
                self.dob is not None,
                self.gender,
                self.category,
                self.is_pwd is not None,
                self.domicile_state,
                self.highest_degree,
                self.stream,
                self.percentage_cgpa is not None,
                self.passing_year is not None,
                bool(self.skills),
            ]
        )


class ClaimDraftIn(CandidateProfileIn):
    """A guest's draft claimed once after sign-in. Must contain something."""

    @model_validator(mode="after")
    def draft_not_empty(self) -> "ClaimDraftIn":
        if self.is_empty():
            raise ValueError("The draft is empty; there is nothing to claim.")
        return self


class WeekDoneIn(BaseModel):
    """Toggle a roadmap week done/undone. Extras (e.g. fake percentages) are rejected."""

    model_config = ConfigDict(extra="forbid")

    done: bool


class CandidateProfileOut(BaseModel):
    id: str
    full_name: Optional[str] = None
    dob: Optional[date] = None
    gender: str
    category: str
    is_pwd: bool
    domicile_state: Optional[str] = None
    highest_degree: Optional[str] = None
    stream: Optional[str] = None
    percentage_cgpa: Optional[float] = None
    passing_year: Optional[int] = None
    skills: list[str]


class ClaimDraftOut(BaseModel):
    status: Literal["claimed", "already_claimed"]
    profile: CandidateProfileOut


class RoadmapConcreteOut(BaseModel):
    """A saved roadmap, plus computed server-side progress."""

    roadmap_id: str
    exam_id: str
    target_weeks: int
    roadmap: StudyRoadmapResponse
    created_at: datetime
    completed_weeks: list[int]
    completed_count: int
    percent: int


class ProgressOut(BaseModel):
    roadmap_id: str
    target_weeks: int
    completed_weeks: list[int]
    completed_count: int
    percent: int
