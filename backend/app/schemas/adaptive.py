from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# ----------------------------------------------------
# Base Question Schema
# ----------------------------------------------------
class QuestionItem(BaseModel):
    """A question as shown while the drill is in progress.

    Deliberately excludes ``correct_option`` and ``explanation``: those are
    graded material and must not be readable before the attempt is submitted.
    """

    id: str
    subject: str
    topic: str
    sub_topic: str
    question: str
    options: Dict[str, str]
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
_PARAM_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9 &()./-]{0,79}$"


class QuestionAnswerItem(BaseModel):
    question_id: str = Field(min_length=1, max_length=64)
    # The UI only ever sends the option key, never free text.
    selected_option: str = Field(pattern=r"^[A-Da-d]$")
    time_taken_sec: int = Field(default=0, ge=0, le=3600)


class SubmitQuizPayload(BaseModel):
    exam_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9-]{1,64}$")
    topic: str = Field(min_length=1, max_length=80, pattern=_PARAM_PATTERN)
    # No user_id: the owner always comes from the session cookie.
    answers: List[QuestionAnswerItem] = Field(min_length=1, max_length=50)


class DiagnosticItem(BaseModel):
    question_id: str
    topic: str
    sub_topic: str
    mistake_type: str
    is_repeated: bool = False


class QuestionReviewItem(BaseModel):
    """Post-submission feedback for one question.

    Returned only after the attempt is graded, which is why it may contain the
    answer and the solution.
    """

    question_id: str
    question: str
    options: Dict[str, str]
    selected_option: str
    correct_option: str
    explanation: Optional[str] = None
    is_correct: bool
    time_taken_sec: int


class QuizEvaluationResponse(BaseModel):
    quiz_id: str
    total_attempted: int
    correct_count: int
    accuracy_pct: float
    topic_status: str  # "Mastered" | "Moderate" | "Needs Revision"
    diagnostics: List[DiagnosticItem] = []
    micro_revisions_added: List[str] = []
    results: List[QuestionReviewItem] = []


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
    user_id: int
    exam_id: str
    topics: List[TopicMasteryItem]
