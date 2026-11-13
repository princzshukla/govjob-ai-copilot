from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.candidate import CandidateProfileCreate

RuleStatus = Literal["passed", "failed", "needs_check"]
Verdict = Literal["eligible", "check_manually", "ineligible"]


class RuleExplanation(BaseModel):
    """One eligibility rule, with the values that produced the outcome."""

    rule: str
    candidate_value: str
    required_value: str
    status: RuleStatus
    message: str


class ExamMatchResult(BaseModel):
    exam_id: str
    title: str
    organizing_body: str
    post_type: str
    application_deadline: date
    exam_date: Optional[date]
    official_pdf_url: Optional[str] = None
    is_eligible: bool
    candidate_age_at_cutoff: int
    max_allowed_age: int
    is_last_attempt_age: bool
    reasons_failed: List[str] = Field(default_factory=list)
    syllabus_overlap_pct: Optional[float] = None

    # T7 additions. Defaults keep the existing API contract usable.
    verdict: Verdict = "ineligible"
    check_manually: bool = False
    rules: List[RuleExplanation] = Field(default_factory=list)
    source_url: Optional[str] = None
    last_checked_at: Optional[date] = None


class EligibilityCheckResponse(BaseModel):
    candidate_name: Optional[str]
    eligible_now: List[ExamMatchResult]
    borderline_last_chance: List[ExamMatchResult]
    ineligible: List[ExamMatchResult]
    check_manually: List[ExamMatchResult] = Field(default_factory=list)


class EligibilityReportCreate(BaseModel):
    """A user-submitted report that a stored eligibility result is wrong."""

    exam_id: str
    candidate: CandidateProfileCreate
    reported_verdict: Optional[Verdict] = None
    expected_verdict: Optional[Verdict] = None
    note: Optional[str] = Field(default=None, max_length=2000)


class EligibilityReportResponse(BaseModel):
    report_id: str
    status: str
    exam_id: str
    created_at: datetime
