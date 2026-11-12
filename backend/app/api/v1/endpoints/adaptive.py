import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db  # adjust if your session generator is named differently
from app.models.adaptive import QuestionBank, QuizAttempt, TopicMastery
from app.schemas.adaptive import (
    QuizGenerateResponse,
    SubmitQuizPayload,
    QuizEvaluationResponse,
    UserMasteryResponse,
    TopicMasteryItem,
    DiagnosticItem,
)
from app.services.quiz_service import get_or_generate_quiz

router = APIRouter()


@router.get("/quiz", response_model=QuizGenerateResponse)
async def get_quiz(
    exam_id: str = Query(..., description="Target exam ID (e.g. ssc-cgl-tier1)"),
    subject: str = Query(..., description="Subject domain"),
    topic: str = Query(..., description="Specific syllabus topic"),
    count: int = Query(3, ge=1, le=10),
    user_id: Optional[str] = Query("usr_demo_001", description="Candidate ID to exclude seen questions"),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetches unseen questions for the user from QuestionBank,
    falling back to Groq if cache misses occur.
    """
    questions = await get_or_generate_quiz(
        db=db,
        exam_id=exam_id,
        subject=subject,
        topic=topic,
        user_id=user_id,
        count=count,
    )
    
    quiz_id = f"quiz_{uuid.uuid4().hex[:8]}"
    return QuizGenerateResponse(
        quiz_id=quiz_id,
        exam_id=exam_id,
        topic=topic,
        questions=questions,
        total_questions=len(questions),
    )


@router.post("/submit-quiz", response_model=QuizEvaluationResponse)
async def submit_quiz(
    payload: SubmitQuizPayload,
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluates submissions, performs diagnostic error classification (Rush vs Conceptual),
    updates TopicMastery EMA, and logs QuizAttempt to record candidate drills.
    """
    if not payload.answers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No answers provided."
        )

    # 1. Initialize metrics upfront so they are never unbound
    total_attempted = len(payload.answers)
    correct_count = 0
    diagnostics: List[DiagnosticItem] = []

    # 2. Fetch questions to evaluate correctness and baseline expected timings
    q_ids = [ans.question_id for ans in payload.answers]
    stmt = select(QuestionBank).where(QuestionBank.id.in_(q_ids))
    result = await db.execute(stmt)
    db_questions = {q.id: q for q in result.scalars().all()}

    # 3. Evaluate answers
    for ans in payload.answers:
        q_record = db_questions.get(ans.question_id)
        if not q_record:
            continue

        q_data = q_record.question_data or {}
        correct_option = q_data.get("correct_option")
        expected_time = q_data.get("expected_time_sec", 45)
        is_correct = (
            ans.selected_option.strip().upper() == str(correct_option).strip().upper()
        )

        if is_correct:
            correct_count += 1
        else:
            # Diagnostic Classification: Rush vs Conceptual Gap
            if ans.time_taken_sec < (expected_time * 0.45):
                mistake_type = "Calculation / Rush Error"
            elif ans.time_taken_sec > (expected_time * 1.5):
                mistake_type = "Time-Sink Bottleneck"
            else:
                mistake_type = "Conceptual Gap"

            diagnostics.append(
                DiagnosticItem(
                    question_id=ans.question_id,
                    topic=payload.topic,
                    sub_topic=q_record.sub_topic or payload.topic,
                    mistake_type=mistake_type,
                    is_repeated=False,
                )
            )

    accuracy_pct = (
        round((correct_count / total_attempted) * 100, 1)
        if total_attempted > 0
        else 0.0
    )

    # 4. Log drill attempt into QuizAttempt (matching your model columns)
    attempt = QuizAttempt(
        id=str(uuid.uuid4()),
        user_id=payload.user_id,
        exam_id=payload.exam_id,
        topic=payload.topic,
        score=correct_count,
        total_questions=total_attempted,
        accuracy_percentage=accuracy_pct,
        time_taken_seconds=sum(ans.time_taken_sec for ans in payload.answers),
        diagnostics_log=[d.model_dump() for d in diagnostics],
    )
    db.add(attempt)

    # 5. Update or Insert TopicMastery with Exponential Moving Average (EMA)
    ALPHA = 0.35
    normalized_acc = accuracy_pct / 100.0

    mastery_stmt = select(TopicMastery).where(
        TopicMastery.user_id == payload.user_id,
        TopicMastery.exam_id == payload.exam_id,
        TopicMastery.topic == payload.topic,
    )
    mastery_res = await db.execute(mastery_stmt)
    mastery_record = mastery_res.scalars().first()

    if mastery_record:
        mastery_record.accuracy_ema = round(
            (normalized_acc * ALPHA) + (mastery_record.accuracy_ema * (1 - ALPHA)), 3
        )
        mastery_record.attempts_count += 1
    else:
        mastery_record = TopicMastery(
            id=str(uuid.uuid4()),
            user_id=payload.user_id,
            exam_id=payload.exam_id,
            subject="General",
            topic=payload.topic,
            accuracy_ema=normalized_acc,
            attempts_count=1,
        )
        db.add(mastery_record)

    # Classify Mastery Status
    ema = mastery_record.accuracy_ema
    if ema >= 0.75:
        topic_status = "Mastered"
    elif ema <= 0.45:
        topic_status = "Needs Revision"
    else:
        topic_status = "Moderate"

    mastery_record.status = topic_status

    # 6. Generate micro-revisions if needed
    micro_revisions = []
    if topic_status == "Needs Revision" or any(
        d.mistake_type == "Conceptual Gap" for d in diagnostics
    ):
        micro_revisions = list({d.sub_topic for d in diagnostics}) or [
            f"{payload.topic} Basics"
        ]

    await db.commit()

    return QuizEvaluationResponse(
        quiz_id=f"eval_{uuid.uuid4().hex[:8]}",
        total_attempted=total_attempted,
        correct_count=correct_count,
        accuracy_pct=accuracy_pct,
        topic_status=topic_status,
        diagnostics=diagnostics,
        micro_revisions_added=micro_revisions,
        roadmap_structure_changed=len(micro_revisions) > 0,
    )


@router.get("/mastery/{user_id}/{exam_id}", response_model=UserMasteryResponse)
async def get_user_mastery(
    user_id: str,
    exam_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns all topic masteries for a user on a given exam.
    """
    stmt = select(TopicMastery).where(
        TopicMastery.user_id == user_id,
        TopicMastery.exam_id == exam_id,
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    topics = [
        TopicMasteryItem(
            topic=r.topic,
            subject=r.subject or "General",
            accuracy_ema=r.accuracy_ema,
            attempts_count=r.attempts_count,
            status=r.status,
            last_reviewed_at=str(r.last_reviewed_at) if r.last_reviewed_at else "",
        )
        for r in records
    ]

    return UserMasteryResponse(
        user_id=user_id,
        exam_id=exam_id,
        topics=topics,
    )