"""Quiz generation + caching, with a hardened LLM boundary.

Every value crossing the model boundary is normalised and validated on write:
nothing model-produced enters ``question_bank`` unless it has a non-empty
question (min 10 chars), a normalised ``A-D`` option map, and a
``correct_option`` that actually exists in those options. Malformed output is
skipped (never persisted); a batch with no usable questions raises
``QuizGenerationError`` so the endpoint can answer 502 instead of serving an
empty or poisoned quiz to other accounts.
"""

import json
import logging
import uuid
from typing import List

import httpx
from groq import AsyncGroq
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.adaptive import QuestionBank
from app.schemas.adaptive import QuestionItem

logger = logging.getLogger(__name__)

# Per-request HTTP timeout keeps a stalled Groq call from pinning a pooled
# DB/worker thread forever.
_GROQ_TIMEOUT = httpx.Timeout(30.0, connect=5.0)

groq_client = (
    AsyncGroq(api_key=settings.GROQ_API_KEY, timeout=_GROQ_TIMEOUT)
    if getattr(settings, "GROQ_API_KEY", None)
    else None
)

_OPTION_KEYS = ("A", "B", "C", "D")
_DIFFICULTIES = {"Easy", "Medium", "Hard"}


class QuizGenerationError(RuntimeError):
    """The model returned nothing usable. Callers turn this into a 502."""


def _clean_str(value: object, default: str | None = None) -> str | None:
    if value is None:
        return default
    if not isinstance(value, str):
        value = str(value)
    cleaned = " ".join(str(value).split())
    return cleaned or default


def _normalise_options(options: object) -> dict[str, str] | None:
    """Normalise options to {A: ..., B: ..., C: ..., D: ...}.

    Accepts either the ``{"A": "text", ...}`` dict or a bare list
    ``["a", "b", "c", "d"]``. Values are coerced to non-empty strings. Anything
    that does not yield at least two identifiable options is rejected.
    """
    if isinstance(options, list):
        mapped: dict[str, str] = {}
        for index, item in enumerate(options):
            if index >= 4:
                break
            text = _clean_str(item)
            if text:
                mapped[_OPTION_KEYS[index]] = text
        return mapped if len(mapped) >= 2 else None

    if isinstance(options, dict):
        mapped = {}
        for key, value in options.items():
            letter = str(key).strip().upper()[:1]
            if letter in _OPTION_KEYS:
                text = _clean_str(value)
                if text:
                    mapped[letter] = text
        return mapped if len(mapped) >= 2 else None

    return None


def _normalise_question(raw: object, topic: str) -> dict | None:
    """Normalise one model-produced question. Returns None if unusable."""
    if not isinstance(raw, dict):
        return None

    question = _clean_str(raw.get("question"))
    if not question or len(question) < 10:
        return None

    options = _normalise_options(raw.get("options"))
    if not options:
        return None

    correct = _clean_str(raw.get("correct_option"))
    correct = str(correct).strip().upper()[:1] if correct else ""
    if correct not in options:
        # Unanswerable by construction; never cache or serve it.
        return None

    sub_topic = _clean_str(raw.get("sub_topic")) or _clean_str(topic) or "General"

    difficulty = str(_clean_str(raw.get("difficulty"), "Medium") or "Medium")
    if difficulty not in _DIFFICULTIES:
        difficulty = "Medium"

    try:
        expected = int(raw.get("expected_time_sec") or 45)
    except (TypeError, ValueError):
        expected = 45
    expected = max(5, min(600, expected))

    return {
        "question": question,
        "options": options,
        "correct_option": correct,
        "explanation": _clean_str(raw.get("explanation")),
        "expected_time_sec": expected,
        "difficulty": difficulty,
        "sub_topic": sub_topic,
    }


def _build_question_item(
    record_id: str,
    subject: str,
    topic: str,
    sub_topic: str,
    difficulty: str,
    data: dict,
) -> QuestionItem:
    # Never copy correct_option/explanation into the client payload.
    return QuestionItem(
        id=record_id,
        subject=subject,
        topic=topic,
        sub_topic=sub_topic,
        question=data.get("question", ""),
        options=data.get("options", {}),
        difficulty=difficulty or "Medium",
        expected_time_sec=data.get("expected_time_sec", 45),
    )


def _strip_json_fences(raw: str) -> str:
    text = raw.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    lines = lines[1:]
    while lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


async def get_or_generate_quiz(
    db: AsyncSession,
    exam_id: str,
    subject: str,
    topic: str,
    count: int = 3,
) -> List[QuestionItem]:
    """
    1. Queries PostgreSQL for cached questions matching exam/subject/topic.
    2. If the cache has fewer than ``count`` questions, synthesizes the delta
       via Groq (with every field normalised and validated on write).
    3. Persists new questions and returns the combined batch.
    """
    # 1. Base query for cached questions matching exam + subject + topic.
    filters = [
        QuestionBank.topic == topic,
        QuestionBank.exam_id == exam_id,
        QuestionBank.subject == subject,
    ]

    stmt = (
        select(QuestionBank)
        .where(and_(*filters))
        .order_by(QuestionBank.created_at.desc())
        .limit(count)
    )
    result = await db.execute(stmt)
    cached_records = result.scalars().all()

    cached_items: List[QuestionItem] = []
    for record in cached_records:
        raw = record.question_data if isinstance(record.question_data, dict) else {}
        normalised = _normalise_question(raw, topic)
        if not normalised:
            # Legacy/poisoned rows are never served; they also fail loudly in
            # the audit trail rather than becoming a silent 500 for every user.
            logger.warning("Skipping malformed cached question id=%s", record.id)
            continue
        cached_items.append(
            _build_question_item(
                record_id=record.id,
                subject=record.subject,
                topic=record.topic,
                sub_topic=normalised["sub_topic"],
                difficulty=normalised["difficulty"],
                data=normalised,
            )
        )

    # If cache has enough questions, return immediately ($0 LLM cost)
    if len(cached_items) >= count:
        return cached_items[:count]

    # 2. Cache miss / delta generation via Groq
    needed = count - len(cached_items)
    # The inputs behind these interpolation points are pattern-constrained by
    # the endpoint (see adaptive.get_quiz), which keeps the prompt size and
    # shape stable; values are never asked to "ignore instructions".
    prompt = f"""
Generate exactly {needed} multiple-choice questions for Indian Government Exam ({exam_id}).
Subject: {subject}
Topic: {topic}

Return ONLY a JSON object with a single key "questions" containing an array of objects.
Each object MUST have the following keys:
- "sub_topic": specific subtopic string (e.g. Successive Percentage, Markup)
- "question": clear question text
- "options": object with keys "A", "B", "C", "D"
- "correct_option": "A", "B", "C", or "D"
- "explanation": step-by-step mathematical or logical solution
- "difficulty": "Easy", "Medium", or "Hard"
- "expected_time_sec": integer seconds (e.g. 45 to 90)

The sub_topic and question MUST concern the requested topic ({topic}). Do not invent unrelated subjects.
"""

    if not groq_client:
        raise QuizGenerationError("GROQ_API_KEY is not configured in settings.")

    model = settings.GROQ_MODEL
    try:
        response = await groq_client.chat.completions.create(
            model=model,
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
    except Exception:
        # Never leak upstream bodies to the client; log for operators only.
        logger.exception("Groq request failed for model=%s", model)
        raise QuizGenerationError("The question generator is unavailable right now.")

    raw_text = response.choices[0].message.content or "{}"
    try:
        parsed = json.loads(_strip_json_fences(raw_text))
    except json.JSONDecodeError:
        logger.warning("Model returned invalid JSON for topic=%r", topic)
        raise QuizGenerationError("The question generator returned unusable output.")

    if isinstance(parsed, dict):
        questions_list = parsed.get("questions", [])
    elif isinstance(parsed, list):
        questions_list = parsed
    else:
        questions_list = []

    if not isinstance(questions_list, list):
        questions_list = []

    new_items: List[QuestionItem] = []
    for raw in questions_list:
        normalised = _normalise_question(raw, topic)
        if not normalised:
            continue  # skip malformed rows instead of persisting poison

        q_id = str(uuid.uuid4())
        db_q = QuestionBank(
            id=q_id,
            exam_id=exam_id,
            subject=subject,
            topic=topic,
            sub_topic=normalised["sub_topic"],
            difficulty=normalised["difficulty"],
            question_data={
                "question": normalised["question"],
                "options": normalised["options"],
                "correct_option": normalised["correct_option"],
                "explanation": normalised["explanation"],
                "expected_time_sec": normalised["expected_time_sec"],
            },
        )
        db.add(db_q)

        new_items.append(
            _build_question_item(
                record_id=q_id,
                subject=subject,
                topic=topic,
                sub_topic=normalised["sub_topic"],
                difficulty=normalised["difficulty"],
                data=normalised,
            )
        )

    if not new_items:
        # Cache had fewer than requested and the model produced nothing usable:
        # do NOT return an empty quiz with HTTP 200.
        await db.rollback()
        raise QuizGenerationError("The question generator produced no usable questions.")

    await db.commit()

    return (cached_items + new_items)[:count]
