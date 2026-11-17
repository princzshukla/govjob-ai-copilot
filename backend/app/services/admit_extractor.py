"""Layer 2 for admit cards — minimal extraction with the same trust rules.

Admit cards carry no eligibility criteria; the official download link is the
discovered notice URL itself, so the only fields worth reading are the exam
name and the dates. Bar stays "flag, never guess": low confidence, missing
exam name (and no usable headline), scanned PDFs → ``needs_manual_review``.
"""
from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from . import notification_extractor as nx
from .notification_extractor import (
    _fallback_completion,
    _groq_completion,
)
from app.schemas.pipeline import AdmitCardExtraction, AdmitCardExtractionResult

logger = logging.getLogger(__name__)

TOKEN_BUDGET = 2500
MIN_CONFIDENCE = nx.MIN_CONFIDENCE

_SYSTEM_PROMPT = "You output only valid JSON objects."

_FIELD_KEYS = {"exam_name", "exam_date", "notification_date"}


def _build_prompt(raw_text: str, budget: float = TOKEN_BUDGET) -> str:
    return f"""Extract fields from this Indian government admit card / exam-city intimation notice.
Return a JSON object. Every field MUST be an object:
{{"value": <value or null>, "confidence": <0.0-1.0>, "evidence": "<exact quote ≤140 chars from the document, or null>"}}

Keys:
- "exam_name": full name of the examination as written (e.g. "Sub-Inspector in Delhi Police and CAPFs Examination, 2025"), or null
- "exam_date": the day of the (first) examination, "YYYY-MM-DD", or null
- "notification_date": the date this admit card / notice was released, "YYYY-MM-DD", or null
- "confidence": number 0.0-1.0 — your confidence in the JSON's accuracy as a whole

STRICT RULES:
1. Use ONLY what is explicitly written in the document. Never infer, estimate, or complete missing values.
2. If a value is ambiguous, conflicting, or absent, set value=null and confidence<=0.3 for it.
3. Dates must be real calendar dates present in the document.
4. Evidence snippets must be copied verbatim from the document — no paraphrase.
5. Return ONLY the JSON object. No commentary.

DOCUMENT TEXT (compressed; intro plus keyword-marked sections of the full document):
{nx.compress_for_prompt(raw_text, budget)}"""


def _parse_llm_payload(parsed: object) -> tuple[AdmitCardExtraction, str | None]:
    if not isinstance(parsed, dict):
        return AdmitCardExtraction(), "top-level JSON is not an object"

    body: dict[str, object] = {}
    field_confidence: dict[str, float] = {}
    evidence: dict[str, str] = {}

    for key, raw in parsed.items():
        if key in _FIELD_KEYS:
            if isinstance(raw, dict) and ("value" in raw):
                value = raw.get("value")
                conf = raw.get("confidence")
                ev = raw.get("evidence")
                try:
                    field_confidence[key] = max(0.0, min(1.0, float(conf))) if conf is not None else 0.5
                except (TypeError, ValueError):
                    field_confidence[key] = 0.5
                if isinstance(ev, str) and ev.strip():
                    evidence[key] = ev.strip()[:200]
            else:
                value = raw  # bare scalar — accepted, penalized
                field_confidence[key] = 0.5
            body[key] = value
        elif key == "confidence" and isinstance(raw, (int, float)):
            body[key] = float(raw)

    try:
        extraction = AdmitCardExtraction.model_validate(
            {**body, "field_confidence": field_confidence, "evidence": evidence}
        )
    except ValidationError as exc:
        return AdmitCardExtraction(), f"schema validation failed: {exc}"

    core = [f for f in ("exam_name", "exam_date", "notification_date") if getattr(extraction, f) not in (None, "")]
    if core:
        extraction.confidence = min(field_confidence.get(f, 0.6) for f in core)
    else:
        extraction.confidence = 0.0
    return extraction, None


def _validate_and_flag(
    result: AdmitCardExtraction,
    raw_chars: int,
    is_scanned: bool,
    provider: str,
    *,
    headline: str | None,
) -> AdmitCardExtractionResult:
    reasons: list[str] = []

    if not (result.exam_name or headline):
        reasons.append("exam_name missing (PDF states none and link has no headline)")
    if result.confidence < MIN_CONFIDENCE:
        reasons.append(f"confidence {result.confidence:.2f} below {MIN_CONFIDENCE}")

    return AdmitCardExtractionResult(
        **result.model_dump(),
        raw_text_chars=raw_chars,
        is_scanned=is_scanned,
        needs_manual_review=bool(reasons) or is_scanned,
        review_reasons=reasons + (["scanned/image-only PDF — no text layer"] if is_scanned else []),
        provider=provider,
    )


async def extract_admit_card(
    pdf_bytes: bytes, *, headline: str | None = None
) -> AdmitCardExtractionResult:
    text, page_count, chars_per_page = nx.extract_text_stats(pdf_bytes)

    if chars_per_page < nx.MIN_CHARS_PER_PAGE:
        logger.info("admit-card PDF looks scanned (%.0f chars/page over %d pages)", chars_per_page, page_count)
        return AdmitCardExtractionResult(
            confidence=0.0,
            raw_text_chars=len(text),
            is_scanned=True,
            needs_manual_review=True,
            review_reasons=[f"scanned/image-only PDF — {chars_per_page:.0f} chars/page, no usable text layer"],
        )

    cleaned = nx.clean_raw_text(text)

    def make_messages(budget: float) -> list[dict]:
        return [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_prompt(cleaned, budget)},
        ]

    messages = make_messages(float(TOKEN_BUDGET))
    try:
        raw = await _groq_completion(make_messages)
    except Exception as exc:
        logger.warning("admit-card LLM failed after retries: %s — trying fallback", exc)
        raw = await _fallback_completion(messages)
        if raw is None:
            return AdmitCardExtractionResult(
                confidence=0.0,
                raw_text_chars=len(cleaned),
                needs_manual_review=True,
                review_reasons=[f"LLM unavailable: {exc}"],
                provider="unavailable",
            )

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("admit-card LLM output is not JSON: %s", exc)
        parsed = {}

    extraction, parse_error = _parse_llm_payload(parsed)
    if parse_error:
        return AdmitCardExtractionResult(
            confidence=0.0,
            raw_text_chars=len(cleaned),
            needs_manual_review=True,
            review_reasons=[f"LLM output unparseable/invalid: {parse_error}"],
        )

    # Prefer the source's own headline for the exam name when the PDF only
    # implies it — but keep the extraction's confidence, never raise it.
    if not extraction.exam_name and headline:
        extraction.exam_name = headline.strip()[:255]
        extraction.field_confidence["exam_name"] = 0.5

    return _validate_and_flag(extraction, raw_chars=len(cleaned), is_scanned=False, provider="groq", headline=headline)
