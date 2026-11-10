# app/schemas/adaptive.py
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime

class QuestionItem(BaseModel):
    id: str
    subject: str
    topic: str
    sub_topic: Optional[str] = None
    question: str
    options: Dict[str, str] # {"A": "...", "B": "...", "C": "...", "D": "..."}
    correct_option: str
    explanation: str
    difficulty: str = "Medium"
    expected_time_sec: int = 45

class QuizResponse(BaseModel):
    quiz_id: str
    exam_id: str
    topic: str
    questions: List[QuestionItem]
    total_questions: int

class UserAnswerSubmission(BaseModel):
    question_id: str
    selected_option: str
    time_taken_sec: int

class QuizSubmitRequest(BaseModel):
    user_id: str
    exam_id: str
    topic: str
    answers: List[UserAnswerSubmission]

class MistakeReport(BaseModel):
    question_id: str
    topic: str
    sub_topic: str
    mistake_type: str
    is_repeated: bool

class QuizResultResponse(BaseModel):
    quiz_id: str
    total_attempted: int
    correct_count: int
    accuracy_pct: float
    topic_status: str
    diagnostics: List[MistakeReport]
    micro_revisions_added: List[Dict]
    roadmap_structure_changed: bool = False