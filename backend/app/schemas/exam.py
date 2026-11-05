from pydantic import BaseModel
from typing import List, Optional
from datetime import date

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
    reasons_failed: List[str] = []
    syllabus_overlap_pct: Optional[float] = None

    
class EligibilityCheckResponse(BaseModel):
    candidate_name: Optional[str]
    eligible_now: List[ExamMatchResult]
    borderline_last_chance: List[ExamMatchResult]
    ineligible: List[ExamMatchResult]