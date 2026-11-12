from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# ----------------------------------------------------
# Base Question Schema
# ----------------------------------------------------
class QuestionItem(BaseModel):
    id: str
    subject: str
    topic: str
    sub_topic: str
    question: str
    options: Dict[str, str]
    correct_option: str
    explanation: Optional[str] = None
    difficulty: str = "Medium"
    expected_time_sec: int = 45


# ----------------------------------------------------
# Quiz Generation Schemas
# ----------------------------------------------------
class QuizGenerateResponse(BaseModel):
    quiz_id: str
    exam_id: str
    topic: str
    questions: List[QuestionItem]
    total_questions: int


# ----------------------------------------------------
# Quiz Submission & Diagnostics Schemas
# ----------------------------------------------------
class QuestionAnswerItem(BaseModel):
    question_id: str
    selected_option: str
    time_taken_sec: int = 0


class SubmitQuizPayload(BaseModel):
    user_id: str
    exam_id: str
    topic: str
    answers: List[QuestionAnswerItem]


class DiagnosticItem(BaseModel):
    question_id: str
    topic: str
    sub_topic: str
    mistake_type: str
    is_repeated: bool = False


class QuizEvaluationResponse(BaseModel):
    quiz_id: str
    total_attempted: int
    correct_count: int
    accuracy_pct: float
    topic_status: str  # "Mastered" | "Moderate" | "Needs Revision"
    diagnostics: List[DiagnosticItem] = []
    micro_revisions_added: List[str] = []
    roadmap_structure_changed: bool = False


# ----------------------------------------------------
# Mastery Tracking Schemas
# ----------------------------------------------------
class TopicMasteryItem(BaseModel):
    topic: str
    subject: str
    accuracy_ema: float
    attempts_count: int
    status: str
    last_reviewed_at: str


class UserMasteryResponse(BaseModel):
    user_id: str
    exam_id: str
    topics: List[TopicMasteryItem]