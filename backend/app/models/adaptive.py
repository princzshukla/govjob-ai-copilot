# app/models/adaptive.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.models.exam import Base

class QuestionBank(Base):
    __tablename__ = "question_bank"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    exam_id = Column(String, index=True, nullable=True) # e.g. "ssc-chsl-12th" or null for general
    subject = Column(String, index=True, nullable=False) # e.g. "Quantitative Aptitude"
    topic = Column(String, index=True, nullable=False)   # e.g. "Percentage"
    sub_topic = Column(String, index=True, nullable=True)# e.g. "Successive Percentage Change"
    difficulty = Column(String, default="Medium")        # Easy, Medium, Hard
    question_data = Column(JSON, nullable=False)         # {question, options, correct_option, explanation}
    created_at = Column(DateTime, default=datetime.utcnow)

class TopicMastery(Base):
    __tablename__ = "topic_mastery"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True, nullable=False)
    exam_id = Column(String, index=True, nullable=False)
    subject = Column(String, nullable=False)
    topic = Column(String, index=True, nullable=False)
    accuracy_ema = Column(Float, default=0.5)            # Rolling accuracy (0.0 to 1.0)
    attempts_count = Column(Integer, default=0)
    status = Column(String, default="Moderate")          # Weak, Moderate, Strong
    consecutive_fails = Column(Integer, default=0)
    last_reviewed_at = Column(DateTime, default=datetime.utcnow)

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True, nullable=False)
    exam_id = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    accuracy_percentage = Column(Float, nullable=False)
    time_taken_seconds = Column(Integer, default=0)
    diagnostics_log = Column(JSON, nullable=True)        # Mistake classifications
    created_at = Column(DateTime, default=datetime.utcnow)