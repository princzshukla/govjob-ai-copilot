import json
import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from groq import AsyncGroq

from app.core.config import settings
from app.models.adaptive import QuestionBank
from app.schemas.adaptive import QuestionItem

groq_client = (
    AsyncGroq(api_key=settings.GROQ_API_KEY)
    if getattr(settings, "GROQ_API_KEY", None)
    else None
)

async def get_or_generate_quiz(
    db: AsyncSession,
    exam_id: str,
    subject: str,
    topic: str,
    count: int = 5,
) -> List[QuestionItem]:
    # 1. Check PostgreSQL Question Bank (Cache Hit = $0)
    stmt = (
        select(QuestionBank)
        .where(QuestionBank.topic == topic)
        .order_by(QuestionBank.created_at.desc())
        .limit(count)
    )
    result = await db.execute(stmt)
    cached_records = result.scalars().all()

    if len(cached_records) >= count:
        items = []
        for r in cached_records:
            data = r.question_data or {}
            items.append(
                QuestionItem(
                    id=r.id,
                    subject=r.subject,
                    topic=r.topic,
                    sub_topic=r.sub_topic,
                    question=data.get("question"),
                    options=data.get("options", {}),
                    correct_option=data.get("correct_option"),
                    explanation=data.get("explanation"),
                    difficulty=r.difficulty,
                    expected_time_sec=data.get("expected_time_sec", 45),
                )
            )
        return items

    # 2. Cache Miss: Generate via Groq
    needed = count - len(cached_records)
    prompt = f"""
Generate {needed} multiple-choice questions for Indian Government Exam ({exam_id}).
Subject: {subject}
Topic: {topic}

Return a JSON object with a single key "questions" containing an array of objects.
Each object must have the following keys:
- "sub_topic": specific subtopic string
- "question": question text
- "options": object with keys "A", "B", "C", "D"
- "correct_option": "A", "B", "C", or "D"
- "explanation": step-by-step solution
- "difficulty": "Easy", "Medium", or "Hard"
- "expected_time_sec": integer seconds (e.g. 45)
"""

    if not groq_client:
        raise RuntimeError("GROQ_API_KEY is not configured in settings.")

    # Use configured model or a valid Groq default
    chosen_model = getattr(settings, "GROQ_MODEL", "openai/gpt-oss-120b")
    if chosen_model == "openai/gpt-oss-120b":
        chosen_model = "lopenai/gpt-oss-120b"

    try:
        response = await groq_client.chat.completions.create(
            model=chosen_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert Indian Government Exam paper setter (SSC, Railway, Banking). Return only valid JSON object with a 'questions' key.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
    except Exception:
        # Fallback to standard fast 8B model if 70B encounters rate or access limits
        response = await groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert Indian Government Exam paper setter. Return only valid JSON with a 'questions' array.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

    raw_text = response.choices[0].message.content
    parsed = json.loads(raw_text)

    if isinstance(parsed, dict):
        questions_list = parsed.get("questions", [])
    elif isinstance(parsed, list):
        questions_list = parsed
    else:
        questions_list = []

    new_items = []
    for q in questions_list:
        q_id = str(uuid.uuid4())
        db_q = QuestionBank(
            id=q_id,
            exam_id=exam_id,
            subject=subject,
            topic=topic,
            sub_topic=q.get("sub_topic", topic),
            difficulty=q.get("difficulty", "Medium"),
            question_data=q,
        )
        db.add(db_q)
        new_items.append(
            QuestionItem(
                id=q_id,
                subject=subject,
                topic=topic,
                sub_topic=q.get("sub_topic", topic),
                question=q.get("question"),
                options=q.get("options", {}),
                correct_option=q.get("correct_option"),
                explanation=q.get("explanation"),
                difficulty=q.get("difficulty", "Medium"),
                expected_time_sec=q.get("expected_time_sec", 45),
            )
        )

    await db.commit()

    existing_items = [
        QuestionItem(
            id=r.id,
            subject=r.subject,
            topic=r.topic,
            sub_topic=r.sub_topic,
            question=(r.question_data or {}).get("question"),
            options=(r.question_data or {}).get("options", {}),
            correct_option=(r.question_data or {}).get("correct_option"),
            explanation=(r.question_data or {}).get("explanation"),
            difficulty=r.difficulty,
            expected_time_sec=(r.question_data or {}).get("expected_time_sec", 45),
        )
        for r in cached_records
    ]
    return (existing_items + new_items)[:count]