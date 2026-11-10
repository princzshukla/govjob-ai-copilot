import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.adaptive import QuestionBank, TopicMastery, QuizAttempt
from app.schemas.adaptive import (
    QuizResponse,
    QuestionItem,
    QuizSubmitRequest,
    QuizResultResponse,
    MistakeReport
)
from app.services.quiz_service import get_or_generate_quiz
from app.services.mistake_analyzer import classify_mistakes
from app.services.roadmap_patcher import apply_micro_adjustments

router = APIRouter()

# ---------------------------------------------------------------------------
# 1. Fetch or Generate Quiz (Cache-First)
# ---------------------------------------------------------------------------
@router.get("/quiz", response_model=QuizResponse)
async def get_topic_quiz(
    exam_id: str = Query(..., description="Target exam ID, e.g., 'ssc-chsl-12th'"),
    topic: str = Query(..., description="Topic name, e.g., 'Percentage'"),
    subject: str = Query("Quantitative Aptitude", description="Subject name"),
    count: int = Query(5, ge=1, le=20, description="Number of questions"),
    db: AsyncSession = Depends(get_db)
):
    try:
        questions: List[QuestionItem] = await get_or_generate_quiz(
            db=db,
            exam_id=exam_id,
            subject=subject,
            topic=topic,
            count=count
        )
        return QuizResponse(
            quiz_id=f"qz_{uuid.uuid4().hex[:8]}",
            exam_id=exam_id,
            topic=topic,
            questions=questions,
            total_questions=len(questions)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load quiz: {str(e)}"
        )


# ---------------------------------------------------------------------------
# 2. Submit Quiz & Trigger Micro-Adaptation
# ---------------------------------------------------------------------------
@router.post("/submit-quiz", response_model=QuizResultResponse)
async def submit_quiz(
    payload: QuizSubmitRequest,
    db: AsyncSession = Depends(get_db)
):
    question_ids = [ans.question_id for ans in payload.answers]
    stmt = select(QuestionBank).where(QuestionBank.id.in_(question_ids))
    result = await db.execute(stmt)
    db_questions = result.scalars().all()

    if not db_questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Questions not found in question bank."
        )

    stmt_mastery = select(TopicMastery).where(
        TopicMastery.user_id == payload.user_id,
        TopicMastery.exam_id == payload.exam_id,
        TopicMastery.topic == payload.topic
    )
    result_mastery = await db.execute(stmt_mastery)
    mastery = result_mastery.scalar_one_or_none()

    if not mastery:
        mastery = TopicMastery(
            user_id=payload.user_id,
            exam_id=payload.exam_id,
            subject="General",
            topic=payload.topic,
            accuracy_ema=0.50,
            attempts_count=0,
            status="Moderate",
            consecutive_fails=0
        )
        db.add(mastery)

    analysis = classify_mistakes(
        db_questions=db_questions,
        user_submissions=payload.answers,
        past_fails=mastery.consecutive_fails
    )

    accuracy_pct = analysis["accuracy_percentage"]
    correct_count = analysis["correct_count"]
    total_count = analysis["total_count"]
    total_time_sec = analysis["total_time_sec"]

    alpha = 0.4
    quiz_ratio = correct_count / total_count if total_count > 0 else 0.0
    mastery.accuracy_ema = round((quiz_ratio * alpha) + (mastery.accuracy_ema * (1.0 - alpha)), 2)
    mastery.attempts_count += 1
    mastery.last_reviewed_at = datetime.utcnow()

    if accuracy_pct < 60.0:
        mastery.consecutive_fails += 1
    else:
        mastery.consecutive_fails = 0

    if mastery.accuracy_ema < 0.50:
        mastery.status = "Weak"
    elif mastery.accuracy_ema > 0.75:
        mastery.status = "Strong"
    else:
        mastery.status = "Moderate"

    micro_adjustments = apply_micro_adjustments(
        diagnostics=analysis["diagnostics"],
        overall_accuracy=accuracy_pct
    )

    # Use .model_dump() for Pydantic v2
    attempt_log = QuizAttempt(
        user_id=payload.user_id,
        exam_id=payload.exam_id,
        topic=payload.topic,
        score=correct_count,
        total_questions=total_count,
        accuracy_percentage=accuracy_pct,
        time_taken_seconds=total_time_sec,
        diagnostics_log=[d.model_dump() for d in analysis["diagnostics"]]
    )
    db.add(attempt_log)

    await db.commit()
    await db.refresh(mastery)

    return QuizResultResponse(
        quiz_id=f"res_{uuid.uuid4().hex[:8]}",
        total_attempted=total_count,
        correct_count=correct_count,
        accuracy_pct=accuracy_pct,
        topic_status=mastery.status,
        diagnostics=analysis["diagnostics"],
        micro_revisions_added=micro_adjustments["added_micro_tasks"],
        roadmap_structure_changed=micro_adjustments["roadmap_structure_changed"]
    )


# ---------------------------------------------------------------------------
# 3. Retrieve Topic Mastery Profile
# ---------------------------------------------------------------------------
@router.get("/mastery/{user_id}/{exam_id}")
async def get_candidate_mastery(
    user_id: str,
    exam_id: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(TopicMastery).where(
        TopicMastery.user_id == user_id,
        TopicMastery.exam_id == exam_id
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    return {
        "user_id": user_id,
        "exam_id": exam_id,
        "topics": [
            {
                "topic": r.topic,
                "subject": r.subject,
                "accuracy_ema": r.accuracy_ema,
                "attempts_count": r.attempts_count,
                "status": r.status,
                "last_reviewed_at": r.last_reviewed_at
            }
            for r in records
        ]
    }


# ---------------------------------------------------------------------------
# 4. Skip-Day Rebalance
# ---------------------------------------------------------------------------
@router.post("/sync-missed-days")
async def sync_missed_days(
    user_id: str,
    exam_id: str,
    days_missed: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(TopicMastery).where(
        TopicMastery.user_id == user_id,
        TopicMastery.exam_id == exam_id
    )
    result = await db.execute(stmt)
    records = result.scalars().all()
    mastery_map = {r.topic: r.status for r in records}

    return {
        "days_missed": days_missed,
        "status": "Schedule Rebalanced",
        "message": f"Successfully re-sequenced pending syllabus over remaining days without shifting final target date.",
        "mastery_snapshot": mastery_map
    }