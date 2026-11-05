# app/schemas/roadmap.py
from pydantic import BaseModel, Field
from typing import List

class WeeklyMilestone(BaseModel):
    week_number: int = Field(..., description="The sequential week number (e.g., 1, 2, 3)")
    phase: str = Field(..., description="e.g., 'Foundation & Concepts', 'Practice & PYQs', or 'Full Mock Tests & Revision'")
    focus_subject: str = Field(..., description="Primary subject or section focus for the week")
    topics: List[str] = Field(..., description="Specific syllabus sub-topics to complete this week")
    practice_goal: str = Field(..., description="Concrete action item, e.g., 'Solve 50 PYQs on Number Systems'")
    recommended_resources: List[str] = Field(..., description="Standard books, NCERT chapters, or free reference material")

class StudyRoadmapResponse(BaseModel):
    exam_name: str = Field(..., description="Full name of the target government exam")
    total_duration_weeks: int = Field(..., description="Total number of weeks in the study plan")
    weekly_breakdown: List[WeeklyMilestone] = Field(..., description="Week-by-week structured milestones")
    revision_strategy: str = Field(..., description="High-level guidance on mock test frequency and error log maintenance")