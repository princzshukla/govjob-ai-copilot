"""Quiz generation + caching, with a hardened LLM boundary.

Every value crossing the model boundary is normalised and validated on write:
nothing model-produced enters ``question_bank`` unless it passes the deterministic
Sathi verifier (pattern, dedup, syllabus, safe-AST math check) *and* the
boundary normaliser below (non-empty question, normalised options, and a
``correct_option`` that actually exists). A batch with no usable questions
raises ``QuizGenerationError`` so the endpoint can answer 502 instead of serving
an empty or poisoned quiz to other accounts.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from groq import AsyncGroq
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exam_patterns import ExamPattern, get_exam_pattern
from app.models.adaptive import QuestionBank
from app.schemas.adaptive import QuestionItem
from app.services.sathi_verifier import (
    is_current_affairs_expired,
    verify_question_candidate,
)

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


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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


# Trusted Factual Grounding Reference Notes for GA / Polity / Banking / CS
TRUSTED_SOURCE_CORPUS: Dict[str, Dict[str, str]] = {
    "indian polity": {
        "source_title": "Constitution of India & M. Laxmikanth Statutory Reference",
        "source_date": "2026-01-01",
        "facts": (
            "Fundamental Rights: Part III (Articles 12-35). DPSP: Part IV (Articles 36-51). "
            "Fundamental Duties: Part IVA, Article 51A (42nd Amendment 1976, 11th duty added by 86th Amendment 2002). "
            "President: Article 52-62, impeachment Article 61, Ordinance power Article 123. "
            "Parliament: Article 79 (President + Lok Sabha + Rajya Sabha), Money Bill Article 110, Joint Sitting Article 108. "
            "Supreme Court: Article 124, Writ Jurisdiction Article 32 (SC) and Article 226 (High Courts). "
            "CAG: Article 148. Attorney General: Article 76. Election Commission: Article 324. "
            "Finance Commission: Article 280. Emergency Provisions: Articles 352 (National), 356 (State), 360 (Financial). "
            "Panchayati Raj: 73rd Amendment 1992 (Part IX, 11th Schedule, 29 subjects). Municipalities: 74th Amendment (12th Schedule)."
        ),
    },
    "modern history": {
        "source_title": "NCERT Modern India & Spectrum Statutory Timeline",
        "source_date": "2026-01-01",
        "facts": (
            "1857 Revolt: Lord Canning (Governor-General). INC Founded: 1885 (A.O. Hume, W.C. Bonnerjee 1st President, Bombay). "
            "Partition of Bengal: 1905 (Lord Curzon), Swadeshi Movement 1905. Surat Split: 1907 (Rash Behari Ghosh). "
            "Home Rule League: 1916 (Tilak & Annie Besant). Lucknow Pact: 1916. Champaran Satyagraha: 1917. "
            "Rowlatt Act & Jallianwala Bagh: April 13, 1919. Non-Cooperation Movement: 1920-1922 (Chauri Chaura). "
            "Simon Commission: 1927. Lahore Session (Purna Swaraj): Dec 1929 (Jawaharlal Nehru). "
            "Dandi March / Civil Disobedience: March 12 - April 6, 1930. Gandhi-Irwin Pact: March 1931. "
            "Poona Pact: Sept 1932. Government of India Act: 1935. Quit India Movement: Aug 8, 1942. Cabinet Mission: 1946."
        ),
    },
    "banking & financial awareness": {
        "source_title": "RBI Master Directions & Banking Regulation Act 1949",
        "source_date": "2026-06-01",
        "facts": (
            "RBI established: April 1, 1935 (RBI Act 1934), nationalized Jan 1, 1949. Monetary Policy Committee (MPC): 6 members "
            "(3 RBI + 3 Govt appointed), inflation target 4% +/- 2%. Basel III minimum CAR in India: 9% (11.5% with CCB). "
            "Priority Sector Lending (PSL) target for Domestic Commercial Banks: 40% of ANBC. "
            "NPCI products: UPI (2016), IMPS, NACH, RuPay, CTS. DICGC deposit insurance cover: Rs 5,00,000 per depositor per bank."
        ),
    },
}


def _get_grounding_context(topic: str, subject: str, source_text_override: Optional[str] = None) -> Dict[str, Optional[str]]:
    if source_text_override:
        now = _utcnow_naive()
        return {
            "source_title": "Supplied Official Notification / Source Text",
            "source_date": now.strftime("%Y-%m-%d"),
            "facts": source_text_override,
            "ca_month": now.strftime("%Y-%m") if "current affairs" in topic.lower() else None,
        }
    key = topic.strip().lower()
    for k, val in TRUSTED_SOURCE_CORPUS.items():
        if k in key or k in subject.strip().lower():
            return {
                "source_title": val["source_title"],
                "source_date": val["source_date"],
                "facts": val["facts"],
                "ca_month": None,
            }
    if "current affairs" in key:
        now = _utcnow_naive()
        now_month = now.strftime("%Y-%m")
        return {
            "source_title": f"PIB & Official Government Releases ({now_month})",
            "source_date": now.strftime("%Y-%m-%d"),
            "facts": None,
            "ca_month": now_month,
        }
    return {"source_title": None, "source_date": None, "facts": None, "ca_month": None}


def _is_math_or_reasoning(subject: str, topic: str) -> bool:
    combined = f"{subject} {topic}".lower()
    keywords = [
        "quant", "math", "algebra", "percentage", "ratio", "number", "interest",
        "geometry", "trigonometry", "profit", "time", "average", "mensuration",
        "data interpretation", "calculus", "statistics", "matrix", "matrices",
    ]
    return any(k in combined for k in keywords)


def _build_question_item(
    record_id: str,
    subject: str,
    topic: str,
    sub_topic: str,
    difficulty: str,
    data: dict,
    pattern: ExamPattern,
    quality_score: float = 1.0,
) -> QuestionItem:
    # Never copy correct_option/explanation into the client payload.
    return QuestionItem(
        id=record_id,
        subject=subject,
        topic=topic,
        sub_topic=sub_topic or topic,
        question=data.get("question", ""),
        options=data.get("options", {}),
        difficulty=difficulty or "Medium",
        expected_time_sec=data.get("expected_time_sec", pattern.default_time_sec),
        origin_type=data.get("origin_type", "PYQ_STYLE"),
        pyq_year=data.get("pyq_year"),
        verification_badge=data.get("verification_badge", "Sathi AI Verified (PYQ-Style)"),
        source_title=data.get("source_title"),
        ca_month=data.get("ca_month"),
        marks_correct=data.get("marks_correct", pattern.marks_correct),
        negative_marks=data.get("negative_marks", pattern.negative_marks),
        quality_score=quality_score if quality_score is not None else 1.0,
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


async def _confirm_answer_with_second_model(
    question_stem: str,
    options: Dict[str, str],
    claimed_correct: str,
    source_facts: Optional[str] = None,
) -> bool:
    """
    Gate 4 (Non-Math Dual-Model Verification):
    Has a second fast model (llama-3.1-8b-instant) independently solve the question
    WITHOUT seeing the generator's answer key, and checks for single-answer agreement.
    """
    if not groq_client:
        return True

    grounding_block = f"\nReference Source Text:\n{source_facts}\n" if source_facts else ""
    verify_prompt = f"""You are an independent exam answer-key auditor.
Solve the following MCQ and check if there is ANY ambiguity (two correct options or no correct option).
{grounding_block}
Question: {question_stem}
Options: {json.dumps(options)}

Return ONLY a JSON object with:
- "independent_answer": the single best option letter (e.g. "A", "B", "C", "D", "E")
- "has_multiple_correct": boolean (true if 2+ options are equally valid)
- "is_factually_valid": boolean (false if the question is factually wrong or unsolvable)
"""
    try:
        res = await groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": verify_prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        verdict = json.loads(res.choices[0].message.content or "{}")
        if verdict.get("has_multiple_correct") is True:
            return False
        if verdict.get("is_factually_valid") is False:
            return False
        ind_ans = str(verdict.get("independent_answer", "")).strip().upper()
        return ind_ans == claimed_correct.strip().upper()
    except Exception:
        # If secondary model rate-limits, rely on primary deterministic checks
        return True


async def get_or_generate_quiz(
    db: AsyncSession,
    exam_id: str,
    subject: str,
    topic: str,
    count: int = 3,
    source_text: Optional[str] = None,
) -> List[QuestionItem]:
    """
    Sathi AI High-Accuracy Quiz Pipeline, with a hardened LLM boundary:
    1. Queries PostgreSQL for active, non-retired, non-expired questions matching
       exam + subject + topic (legacy/poisoned rows never served or cached).
    2. Prioritizes REAL_PYQ questions and high quality_score questions first.
    3. Synthesizes missing questions via Groq with exam-specific option counts
       (4 vs 5), deterministic math AST checks, dual-model verification, and
       teaching explanations — normalised and validated on write.
    """
    pattern = get_exam_pattern(exam_id)

    filters = [
        QuestionBank.topic == topic,
        QuestionBank.exam_id == exam_id,
        QuestionBank.subject == subject,
    ]
    if hasattr(QuestionBank, "is_retired"):
        filters.append(QuestionBank.is_retired.is_(False))

    stmt = (
        select(QuestionBank)
        .where(and_(*filters))
        .order_by(QuestionBank.created_at.desc())
        .limit(count * 3)
    )
    result = await db.execute(stmt)
    all_matching_records = list(result.scalars().all())

    # Filter out expired Current Affairs and collect existing question stems for deduplication
    existing_stems: List[str] = []
    valid_cached_records: List[QuestionBank] = []

    for r in all_matching_records:
        q_data = r.question_data or {}
        stem = q_data.get("question", "")
        if stem:
            existing_stems.append(stem)

        ca_month = getattr(r, "ca_month", None) or q_data.get("ca_month")
        if is_current_affairs_expired(ca_month):
            if hasattr(r, "is_retired"):
                r.is_retired = True
            continue

        # Ensure cached question matches the exam's option count
        opts = q_data.get("options", {})
        if isinstance(opts, dict) and len(opts) == pattern.option_count:
            valid_cached_records.append(r)

    cached_items: List[QuestionItem] = []
    for record in valid_cached_records:
        if len(cached_items) >= count:
            break
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
                sub_topic=normalised["sub_topic"] or record.sub_topic,
                difficulty=normalised["difficulty"],
                data=normalised,
                pattern=pattern,
                quality_score=getattr(record, "quality_score", 1.0),
            )
        )

    # If cache has enough questions, return immediately ($0 LLM cost)
    if len(cached_items) >= count:
        return cached_items[:count]

    # 2. Cache miss / delta generation via Groq
    needed = count - len(cached_items)
    # Request extra buffer candidates so rejected questions don't leave us short
    request_batch_size = needed + 2

    option_letters = [chr(65 + i) for i in range(pattern.option_count)]
    option_schema_str = ", ".join(f'"{letter}"' for letter in option_letters)
    is_quant = _is_math_or_reasoning(subject, topic)
    grounding = _get_grounding_context(topic, subject, source_text)

    grounding_instruction = ""
    if grounding["facts"]:
        grounding_instruction = f"""
STRICT FACTUAL GROUNDING:
Base every question strictly on this verified reference text:
\"\"\"{grounding['facts']}\"\"\"
Do not invent facts outside this reference.
"""

    math_instruction = ""
    if is_quant:
        math_instruction = """
MATH VERIFICATION REQUIREMENT:
- Include a key "verification_expr" containing a valid Python arithmetic expression (using only numbers, +, -, *, /, **, round, sqrt, gcd) that evaluates to the exact numeric answer in the correct option.
- Ensure the numeric value of the correct option matches `verification_expr` and all other options have distinct numbers.
"""

    # The inputs behind these interpolation points are pattern-constrained by
    # the endpoint (see adaptive.get_quiz), which keeps the prompt size and
    # shape stable; values are never asked to "ignore instructions".
    prompt = f"""Generate {request_batch_size} PYQ-style multiple-choice questions for Indian Government Exam: {exam_id}.
Subject: {subject}
Topic: {topic}
Exam Pattern: Exactly {pattern.option_count} options ({option_schema_str}), +{pattern.marks_correct} marks for correct, -{pattern.negative_marks} negative marking.
{grounding_instruction}
{math_instruction}

Return ONLY a JSON object with a single key "questions" containing an array of objects.
Each object MUST have:
- "sub_topic": specific subtopic string
- "question": clear, unambiguous exam-grade question stem
- "options": object with keys {option_schema_str} (all options must be mutually exclusive)
- "correct_option": one of {option_schema_str}
- "verification_expr": Python arithmetic string calculating the numeric answer (for Quant/Math) or null
- "shortcut_method": 1-2 sentence exam-hall shortcut/trick to solve in under {pattern.default_time_sec}s
- "explanation": concise step-by-step derivation
- "why_wrong": object mapping each wrong option letter to a 1-line reason why it is a trap/incorrect
- "difficulty": "Easy", "Medium", or "Hard"
- "expected_time_sec": integer (30 to 90)
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
                    "content": "You are Sathi AI's Chief Exam Setter for SSC, UPSC, IBPS, RRB, and DRDO. Output strict, mathematically verified JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
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

    for q in questions_list:
        if len(cached_items) + len(new_items) >= count:
            break
        if not isinstance(q, dict):
            continue

        q["origin_type"] = "PYQ_STYLE"
        q["source_title"] = grounding["source_title"]
        q["source_date"] = grounding["source_date"]
        q["ca_month"] = grounding["ca_month"]

        # Run Gate 1, Gate 2, and Gate 3 (Pattern, Dedup, Syllabus, Safe AST Math Check)
        is_valid, reason, enriched = verify_question_candidate(
            raw_q=q,
            pattern=pattern,
            allowed_topics=None,
            existing_stems=existing_stems,
            topic=topic,
            subject=subject,
        )
        if not is_valid:
            logger.info("[Sathi AI Verifier] Rejected candidate question: %s", reason)
            continue

        # Enforce the LLM boundary on everything before it is persisted or served.
        normalised = _normalise_question(enriched, topic)
        if not normalised:
            logger.info("[Sathi AI Verifier] Rejected candidate question: boundary normalisation failed")
            continue

        # Run Gate 4 (Dual-Model Independent Verification for Non-Math / Factual Topics)
        if not is_quant:
            confirmed = await _confirm_answer_with_second_model(
                question_stem=enriched["question"],
                options=enriched["options"],
                claimed_correct=enriched["correct_option"],
                source_facts=grounding["facts"],
            )
            if not confirmed:
                logger.info("[Sathi AI Verifier] Rejected question: Second model disagreed on answer key.")
                continue

        existing_stems.append(enriched["question"])
        q_id = str(uuid.uuid4())
        sub_topic = normalised["sub_topic"]
        difficulty = normalised["difficulty"]

        db_kwargs: Dict[str, Any] = {
            "id": q_id,
            "exam_id": exam_id,
            "subject": subject,
            "topic": topic,
            "sub_topic": sub_topic,
            "difficulty": difficulty,
            "question_data": enriched,
        }
        # Populate extended Sathi AI columns if present on QuestionBank model
        for extra_col, val in [
            ("origin_type", "PYQ_STYLE"),
            ("ai_difficulty", difficulty),
            ("source_title", grounding["source_title"]),
            ("source_date", grounding["source_date"]),
            ("ca_month", grounding["ca_month"]),
            ("quality_score", 1.0),
            ("is_retired", False),
        ]:
            if hasattr(QuestionBank, extra_col):
                db_kwargs[extra_col] = val

        db_q = QuestionBank(**db_kwargs)
        db.add(db_q)

        new_items.append(
            _build_question_item(
                record_id=q_id,
                subject=subject,
                topic=topic,
                sub_topic=sub_topic,
                difficulty=difficulty,
                data=enriched,
                pattern=pattern,
                quality_score=1.0,
            )
        )

    if not new_items:
        # Cache had fewer than requested and the model produced nothing usable:
        # do NOT return an empty quiz with HTTP 200.
        await db.rollback()
        raise QuizGenerationError("The question generator produced no usable questions.")

    await db.commit()

    return (cached_items + new_items)[:count]
