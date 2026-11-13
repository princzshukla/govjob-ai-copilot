# app/models/adaptive.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint

from app.models.exam import Base


class QuestionBank(Base):
    __tablename__ = "question_bank"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    exam_id = Column(String, index=True, nullable=True)       # e.g. "ssc-cgl-general"
    subject = Column(String, index=True, nullable=False)      # e.g. "Quantitative Aptitude"
    topic = Column(String, index=True, nullable=False)        # e.g. "Percentage"
    sub_topic = Column(String, index=True, nullable=True)     # e.g. "Successive Percentage Change"

    # Provenance: Strictly separates real past papers from AI "PYQ-style" drills
    origin_type = Column(String, default="PYQ_STYLE")         # "REAL_PYQ" or "PYQ_STYLE"
    pyq_year = Column(Integer, nullable=True)                 # e.g. 2024 if REAL_PYQ

    # Difficulty: AI initial guess vs Empirical calibration after >= 30 attempts
    difficulty = Column(String, default="Medium")             # Active label ("Easy", "Medium", "Hard")
    ai_difficulty = Column(String, default="Medium")          # Original AI guess
    calibrated_difficulty = Column(String, nullable=True)     # Set from real % correct

    # Factual Grounding & Expiry (GA, Polity, Current Affairs)
    source_title = Column(String, nullable=True)              # e.g. "Laxmikanth Ch. 12 / PIB"
    source_date = Column(String, nullable=True)               # "YYYY-MM-DD"
    ca_month = Column(String(7), index=True, nullable=True)   # "YYYY-MM" (expires after 6 months)

    # Telemetry & Auto-Retirement
    attempts_count = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    avg_time_sec = Column(Float, default=45.0)
    report_count = Column(Integer, default=0)
    quality_score = Column(Float, default=1.0)                # 0.0 to 1.0 health score
    is_retired = Column(Boolean, default=False, index=True)   # True = hidden from drills

    # {
    #   question, options, correct_option, expected_time_sec,
    #   origin_type, pyq_year, marks_correct, negative_marks,
    #   explanation, shortcut_method, why_wrong_map, roadmap_topic_link,
    #   source_title, ca_month, verification_badge
    # }
    question_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class TopicMastery(Base):
    __tablename__ = "topic_mastery"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # Integer FK: mastery belongs to an account row, never to a client string.
    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            name="fk_topic_mastery_user_id",
        ),
        index=True,
        nullable=False,
    )
    exam_id = Column(String, index=True, nullable=False)
    subject = Column(String, nullable=False)
    topic = Column(String, index=True, nullable=False)
    accuracy_ema = Column(Float, default=0.5)
    attempts_count = Column(Integer, default=0)
    status = Column(String, default="Moderate")
    consecutive_fails = Column(Integer, default=0)
    last_reviewed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    __table_args__ = (
        # One mastery row per (user, exam, topic): the endpoint upserts with
        # ON CONFLICT so this is also what keeps upserts atomic.
        UniqueConstraint("user_id", "exam_id", "topic", name="uq_topic_mastery_user_exam_topic"),
    )


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            name="fk_quiz_attempts_user_id",
        ),
        index=True,
        nullable=False,
    )
    exam_id = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    accuracy_percentage = Column(Float, nullable=False)
    net_marks = Column(Float, default=0.0)                    # Accounts for exam negative marking
    time_taken_seconds = Column(Integer, default=0)
    diagnostics_log = Column(JSON, nullable=True)             # Mistake classifications
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
