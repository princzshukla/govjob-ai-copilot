import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.api.v1.deps import current_user, user_or_ip_key
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.adaptive import QuestionBank, QuizAttempt, TopicMastery
from app.models.auth import User
from app.schemas.adaptive import (
    QuizGenerateResponse,
    SubmitQuizPayload,
    QuizEvaluationResponse,
    QuestionReviewItem,
    UserMasteryResponse,
    TopicMasteryItem,
    DiagnosticItem,
)
from app.services.quiz_service import QuizGenerationError, get_or_generate_quiz

router = APIRouter()


@router.get("/quiz", response_model=QuizGenerateResponse)
@limiter.limit("30/hour", key_func=user_or_ip_key)
async def get_quiz(
    request: Request,
    exam_id: str = Query(..., pattern=r"^[a-z0-9-]{1,64}$", description="Target exam ID (e.g. ssc-cgl-tier1)"),
    subject: str = Query(..., pattern=r"^[A-Za-z0-9][A-Za-z0-9 &()./-]{0,63}$", description="Subject domain"),
    topic: str = Query(..., pattern=r"^[A-Za-z0-9][A-Za-z0-9 &()./-]{0,79}$", description="Specific syllabus topic"),
    count: int = Query(3, ge=1, le=10),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetches questions for the logged-in candidate from QuestionBank,
    falling back to Groq if cache misses occur.

    The owner is always the session user; there is no user_id input.
    """
    try:
        questions = await get_or_generate_quiz(
            db=db,
            exam_id=exam_id,
            subject=subject,
            topic=topic,
            count=count,
        )
    except QuizGenerationError as exc:
        # Never leak model output/upstream text; short generic 502 instead of 500.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc) if str(exc) else "The question generator is unavailable right now.",
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
@limiter.limit("60/hour", key_func=user_or_ip_key)
async def submit_quiz(
    request: Request,
    payload: SubmitQuizPayload,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluates submissions, performs diagnostic error classification (Rush vs Conceptual),
    updates TopicMastery EMA, and logs QuizAttempt to record candidate drills.

    The score is always derived from the stored question rows; nothing the client
    sends besides option keys, timing and the topic is trusted.
    """
    if not payload.answers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No answers provided."
        )

    diagnostics: List[DiagnosticItem] = []
    results: List[QuestionReviewItem] = []
    correct_count = 0

    # Fetch questions to evaluate correctness and baseline expected timings.
    # The topic/exam filters stop a client from grading questions from another
    # drill while recording the attempt against this one.
    # De-duplicate answers on question_id (first occurrence wins); identical
    # ids graded twice would double count attempts and score.
    seen_ids: set[str] = set()
    deduped_answers = []
    for ans in payload.answers:
        if ans.question_id in seen_ids:
            continue
        seen_ids.add(ans.question_id)
        deduped_answers.append(ans)

    q_ids = [ans.question_id for ans in deduped_answers]
    stmt = select(QuestionBank).where(
        QuestionBank.id.in_(q_ids),
        QuestionBank.topic == payload.topic,
        QuestionBank.exam_id == payload.exam_id,
    )
    result = await db.execute(stmt)
    db_questions = {q.id: q for q in result.scalars().all()}

    for ans in deduped_answers:
        q_record = db_questions.get(ans.question_id)
        if not q_record:
            # Unknown/foreign question ids are ignored, not counted as attempts.
            continue

        q_data = q_record.question_data or {}
        correct_option = str(q_data.get("correct_option", "")).strip().upper()
        expected_time = q_data.get("expected_time_sec", 45)
        is_correct = ans.selected_option.strip().upper() == correct_option

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

        results.append(
            QuestionReviewItem(
                question_id=ans.question_id,
                question=q_data.get("question", ""),
                options=q_data.get("options", {}),
                selected_option=ans.selected_option.strip().upper(),
                correct_option=correct_option,
                explanation=q_data.get("explanation"),
                is_correct=is_correct,
                time_taken_sec=ans.time_taken_sec,
            )
        )

    total_attempted = len(results)
    if total_attempted == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="None of the submitted questions could be found.",
        )

    accuracy_pct = round((correct_count / total_attempted) * 100, 1)

    attempt = QuizAttempt(
        id=str(uuid.uuid4()),
        user_id=user.id,
        exam_id=payload.exam_id,
        topic=payload.topic,
        score=correct_count,
        total_questions=total_attempted,
        accuracy_percentage=accuracy_pct,
        time_taken_seconds=sum(r.time_taken_sec for r in results),
        diagnostics_log=[d.model_dump() for d in diagnostics],
    )
    db.add(attempt)

    # Update or insert TopicMastery with Exponential Moving Average (EMA).
    # ON CONFLICT keeps one row per (user, exam, topic) even under concurrent
    # submissions; the unique index is created by migration 6f5be5e32e17.
    ALPHA = 0.35
    normalized_acc = accuracy_pct / 100.0

    def _classify(ema: float) -> str:
        if ema >= 0.75:
            return "Mastered"
        elif ema <= 0.45:
            return "Needs Revision"
        return "Moderate"

    # Subject detail comes from the graded question rows (all belong to the
    # subject the drill was generated for); fallback "General" otherwise.
    subject_for_row = next(
        (getattr(q, "subject", None) for q in db_questions.values() if getattr(q, "subject", None)),
        "General",
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    upsert = (
        pg_insert(TopicMastery)
        .values(
            id=str(uuid.uuid4()),
            user_id=user.id,
            exam_id=payload.exam_id,
            subject=subject_for_row[:100],
            topic=payload.topic,
            accuracy_ema=normalized_acc,
            attempts_count=1,
            status=_classify(normalized_acc),
            consecutive_fails=0,
            last_reviewed_at=now,
        )
        .on_conflict_do_update(
            index_elements=["user_id", "exam_id", "topic"],
            set_={
                "accuracy_ema": (normalized_acc * ALPHA)
                + TopicMastery.accuracy_ema * (1 - ALPHA),
                "attempts_count": TopicMastery.attempts_count + 1,
                "last_reviewed_at": now,
            },
        )
        .returning(TopicMastery.id, TopicMastery.accuracy_ema)
    )
    mastery_id, ema = (await db.execute(upsert)).one()
    ema = float(ema or 0.5)
    topic_status = _classify(ema)
    await db.execute(
        update(TopicMastery).where(TopicMastery.id == mastery_id).values(status=topic_status)
    )

    # Generate micro-revisions if needed
    micro_revisions = []
    if topic_status == "Needs Revision" or any(
        d.mistake_type == "Conceptual Gap" for d in diagnostics
    ):
        micro_revisions = list(dict.fromkeys(d.sub_topic for d in diagnostics)) or [
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
        results=results,
    )


@router.get("/mastery/{exam_id}", response_model=UserMasteryResponse)
@limiter.limit("120/hour", key_func=user_or_ip_key)
async def get_user_mastery(
    request: Request,
    exam_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns all topic masteries for the logged-in user on a given exam.
    """
    stmt = select(TopicMastery).where(
        TopicMastery.user_id == user.id,
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
        user_id=user.id,
        exam_id=exam_id,
        topics=topics,
    )
