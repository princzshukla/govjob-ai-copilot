import json
import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from groq import AsyncGroq

from app.core.config import settings
from app.models.adaptive import QuestionBank
from app.schemas.adaptive import QuestionItem

groq_client = (
    AsyncGroq(api_key=settings.GROQ_API_KEY)
    if getattr(settings, "GROQ_API_KEY", None)
    else None
)

def _build_question_item(record_id: str, subject: str, topic: str, sub_topic: str, difficulty: str, data: dict) -> QuestionItem:
    # Never copy correct_option/explanation into the client payload.
    return QuestionItem(
        id=record_id,
        subject=subject,
        topic=topic,
        sub_topic=sub_topic,
        question=data.get("question", ""),
        options=data.get("options", {}),
        difficulty=difficulty,
        expected_time_sec=data.get("expected_time_sec", 45),
    )

async def get_or_generate_quiz(
    db: AsyncSession,
    exam_id: str,
    subject: str,
    topic: str,
    count: int = 3,
) -> List[QuestionItem]:
    """
    1. Queries PostgreSQL for cached questions matching topic/exam.
    2. If cache has fewer than `count` questions, synthesizes the delta via Groq.
    3. Persists new questions to QuestionBank and returns the combined batch.
    """
    # 1. Base query for cached questions matching topic and exam
    filters = [QuestionBank.topic == topic, QuestionBank.exam_id == exam_id]

    stmt = (
        select(QuestionBank)
        .where(and_(*filters))
        .order_by(QuestionBank.created_at.desc())
        .limit(count)
    )
    result = await db.execute(stmt)
    cached_records = result.scalars().all()

    cached_items: List[QuestionItem] = [
        _build_question_item(
            record_id=r.id,
            subject=r.subject,
            topic=r.topic,
            sub_topic=r.sub_topic,
            difficulty=r.difficulty,
            data=r.question_data or {},
        )
        for r in cached_records
    ]

    # If cache has enough questions, return immediately ($0 LLM cost)
    if len(cached_items) >= count:
        return cached_items[:count]

    # 2. Cache Miss / Delta Generation via Groq
    needed = count - len(cached_items)
    prompt = f"""
Generate exactly {needed} multiple-choice questions for Indian Government Exam ({exam_id}).
Subject: {subject}
Topic: {topic}

Return ONLY a JSON object with a single key "questions" containing an array of objects.
Each object must have the following keys:
- "sub_topic": specific subtopic string (e.g. Successive Percentage, Markup)
- "question": clear question text
- "options": object with keys "A", "B", "C", "D"
- "correct_option": "A", "B", "C", or "D"
- "explanation": step-by-step mathematical or logical solution
- "difficulty": "Easy", "Medium", or "Hard"
- "expected_time_sec": integer seconds (e.g. 45 to 90)
"""

    if not groq_client:
        raise RuntimeError("GROQ_API_KEY is not configured in settings.")

    # Primary model (70B) with fast fallback (8B)
    primary_model = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
    fallback_model = "llama-3.1-8b-instant"

    try:
        response = await groq_client.chat.completions.create(
            model=primary_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert Indian Government Exam paper setter (SSC CGL/CHSL, Railways, Banking). Output strict JSON matching the schema.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
    except Exception as err:
        print(f"Primary model {primary_model} failed ({err}). Retrying with {fallback_model}...")
        response = await groq_client.chat.completions.create(
            model=fallback_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert Indian Government Exam paper setter. Output strict JSON with a 'questions' array.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )

    raw_text = response.choices[0].message.content or "{}"
    parsed = json.loads(raw_text)

    if isinstance(parsed, dict):
        questions_list = parsed.get("questions", [])
    elif isinstance(parsed, list):
        questions_list = parsed
    else:
        questions_list = []

    new_items: List[QuestionItem] = []
    for q in questions_list:
        q_id = str(uuid.uuid4())
        sub_topic = q.get("sub_topic", topic)
        difficulty = q.get("difficulty", "Medium")

        db_q = QuestionBank(
            id=q_id,
            exam_id=exam_id,
            subject=subject,
            topic=topic,
            sub_topic=sub_topic,
            difficulty=difficulty,
            question_data=q,
        )
        db.add(db_q)

        new_items.append(
            _build_question_item(
                record_id=q_id,
                subject=subject,
                topic=topic,
                sub_topic=sub_topic,
                difficulty=difficulty,
                data=q,
            )
        )

    await db.commit()

    return (cached_items + new_items)[:count]