"""Layer 2 — LLM extraction of structured fields from notification PDFs.

Design rules (a wrong age limit auto-published costs a candidate their one
shot, so the bar is "flag, never guess"):

* Scanned/image-only PDFs (no extractable text layer) are NEVER sent to the
  LLM — it would invent values. They go straight to manual review with
  ``is_scanned=True``.
* Boilerplate (running headers/footers, page numbers) is stripped before
  prompting, and the document is compressed into the token budget by keeping
  the eligibility-relevant sections (vacancies, ages, dates, qualifications,
  pay). Long PDFs never hit the rate limit as one giant prompt.
* The primary call is retried on 429/5xx and 413 (token budget shrinks) with
  Retry-After-aware backoff — never a bare wait-out.
* A low-confidence/missing-criticals extraction escalates once to a fallback
  OpenAI-compatible endpoint (see ``LLM_FALLBACK_*`` in config) when set.
* The LLM is instructed to emit null for anything not explicitly present, at
  temperature 0, and must return a per-field confidence (0-1) and an evidence
  snippet quoted from the document.
* Extracted values are sanity-checked deterministically. Anything failing
  validation, any missing critical field, or low confidence flags the row for
  manual review instead of auto-publishing into ``exam_notifications``.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from collections import Counter
from datetime import date

import httpx
import pymupdf
from groq import AsyncGroq

from app.core.config import settings
from app.schemas.pipeline import ExtractionResult, NotificationExtraction

logger = logging.getLogger(__name__)

_client: AsyncGroq | None = None


def _groq() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    return _client


CRITICAL_FIELDS = (
    "total_vacancies",
    "age_max_general",
    "age_cutoff_date",
    "required_qualification",
    "application_last_date",
    "pay_level",
)
MIN_CONFIDENCE = 0.7
MIN_CHARS_PER_PAGE = 50  # below this the PDF is effectively image-only
MAX_ATTEMPTS = 4
TOKEN_BUDGET = 6000
_INTRO_TOKENS = 2200

_SYSTEM_PROMPT = "You output only valid JSON objects."
_RELATION_KEYS = {"SC", "ST", "OBC", "OBC-NCL", "EWS", "PWD", "PWBD", "EXSM", "EX-SERVICEMAN", "ST-OBCNCL"}


# ---------------------------------------------------------------------------
# Text preparation
# ---------------------------------------------------------------------------

def clean_raw_text(text: str) -> str:
    """Strip running headers/footers and page furniture before prompting.

    Lines repeated verbatim >= 3 times with < 200 chars are boilerplate
    (firm name, page headers). Pure page-number and rule lines are dropped.
    """
    lines = text.splitlines()
    norm = [re.sub(r"\s+", " ", l.strip().lower()) for l in lines]
    freq = Counter(n for n in norm if n)
    page_num = re.compile(r"^(page\s*)?\d{1,3}\s*(of\s*\d{1,3})?$|^[-–—_]\s*\d{1,3}\s*[-–—_]$")
    kept: list[str] = []
    for line, n in zip(lines, norm):
        s = line.strip()
        if not s:
            kept.append("")
            continue
        # Running headers/footers: long prose lines repeated verbatim. Short
        # table-row cells ("TOTAL") repeat too and must be preserved.
        if len(s) >= 25 and n and freq[n] >= 3:
            words = s.split()
            if len(words) >= 4 and any(c.isalpha() for c in s) and not any(c.isdigit() for c in s):
                continue
        if page_num.match(s.lower()):
            continue
        if set(s) <= set("_-=·~. "):
            continue
        kept.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def _est_tokens(text: str) -> float:
    # ASCII ≈ 1 token / 4 chars; Devanagari & similar scripts ≈ 1 token per char.
    return sum(1 if ord(c) < 128 else 4.0 for c in text) / 4.0


_STRONG_WINDOWS = [
    # (pattern, chars before, chars after, max external matches, priority)
    (re.compile(r"\bTOTAL\b\s*\n?\s*\d", re.I), 80, 250, 4, 0),   # annexure-total tables
    (re.compile(r"\b(last date|closing date|deadline)\b", re.I), 200, 500, 2, 1),
    (re.compile(r"\b(qualif\w*|degree|graduat\w*|diploma)\b", re.I), 200, 700, 8, 1),
    (re.compile(r"\b(age|ages)\b", re.I), 200, 700, 4, 1),
    (re.compile(r"\bvacan\w*", re.I), 200, 400, 8, 2),
    (re.compile(r"\b(pay|salary|scale|ctc|remuner\w*|emolument|level)\b", re.I), 200, 500, 3, 2),
    (re.compile(r"\b(interview|walk.?in)\b", re.I), 200, 350, 2, 3),
]


def _merge_windows(windows: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for a, b in sorted(windows):
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def compress_for_prompt(text: str, budget: float = TOKEN_BUDGET) -> str:
    """Intro plus keyword-marked sections, capped by estimated token budget."""
    if _est_tokens(text) <= budget:
        return text
    parts: list[str] = []
    intro: list[str] = []
    used = 0.0
    for ch in text:
        t = (1 if ord(ch) < 128 else 2.5) / 4.0
        if used + t > _INTRO_TOKENS:
            break
        intro.append(ch)
        used += t
    intro_text = "".join(intro)
    parts.append(intro_text)
    used = _est_tokens(intro_text)
    windows: list[tuple[int, int, int]] = []
    intro_len = len(intro_text)
    for pattern, before, after, limit, priority in _STRONG_WINDOWS:
        count = 0
        for match in pattern.finditer(text):
            a = max(0, match.start() - before)
            b = min(len(text), match.end() + after)
            if a < intro_len:
                if b <= intro_len + 150:
                    continue  # entirely inside the (already kept) intro
                a = intro_len
            if a >= b:
                continue
            windows.append((priority, a, b))
            count += 1
            if count >= limit:
                break
    # Consume in priority order (priority 0 windows first); overlapping
    # windows are merged within a priority so tokens are never double-counted.
    exhausted = False
    for priority in (0, 1, 2, 3):
        if exhausted:
            break
        windows_by_prio = [(a, b) for p, a, b in windows if p == priority]
        for a, b in _merge_windows(windows_by_prio):
            chunk = text[a:b]
            t = _est_tokens(chunk)
            if used + t > budget:
                keep = int((budget - used) / max(t, 1e-9) * len(chunk))
                if keep <= 200:
                    if budget - used <= 0:
                        exhausted = True
                        break
                    continue
                chunk = chunk[:keep]
                t = _est_tokens(chunk)
            parts.append(chunk)
            used += t
            if used >= budget:
                exhausted = True
                break
    return "\n … \n".join(parts)


def extract_text_stats(pdf_bytes: bytes) -> tuple[str, int, float]:
    """Returns (text, page_count, chars_per_page)."""
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        pages = [page.get_text() for page in doc]
    text = "\n".join(pages).strip()
    page_count = max(len(pages), 1)
    return text, page_count, len(text) / page_count


# ---------------------------------------------------------------------------
# Prompt & parsing
# ---------------------------------------------------------------------------

def _build_prompt(raw_text: str, budget: float = TOKEN_BUDGET) -> str:
    return f"""Extract fields from this Indian government recruitment notification.
Return a JSON object. Every field MUST be an object:
{{"value": <value or null>, "confidence": <0.0-1.0>, "evidence": "<exact quote ≤140 chars from the document, or null>"}}

Keys:
- "total_vacancies": integer total vacancies across all posts in this advertisement, or null
- "min_age": minimum age in whole years, or null
- "age_max_general": maximum age in whole years for the GENERAL category (before any relaxation), or null. If the advertisement covers posts with different limits, return the limit for the primary/majority post and lower your confidence.
- "age_relaxations": object mapping category → extra years over the general limit, e.g. {{"SC": 5, "ST": 5, "OBC": 3, "PwBD": 10}}. Use ONLY relaxations explicitly stated in the document; empty object if the document does not state them.
- "age_cutoff_date": date on which age must be reckoned, "YYYY-MM-DD", or null
- "required_qualification": degree AND stream as written (e.g. "B.Tech (Computer Science/IT)"), or null
- "application_last_date": last date to submit the application (for walk-in engagements, the interview date), "YYYY-MM-DD", or null
- "pay_level": pay level/scale/salary as written (e.g. "Level 4 (Rs. 25,500-81,100)"), or null
- "confidence": number 0.0-1.0 — your confidence in the JSON's accuracy as a whole (usually the lowest confidence among the critical fields)

STRICT RULES:
1. Use ONLY what is explicitly written in the document. Never infer, estimate, or complete missing values.
2. If a value is ambiguous, conflicting, or absent, set value=null and confidence<=0.3 for it.
3. Dates must be real calendar dates present in the document.
4. min_age (when present) must be <= age_max_general.
5. Evidence snippets must be copied verbatim from the document — no paraphrase.
6. If the advertisement covers several posts with different vacancies/ages, sum the vacancies, use the primary post's age limit, and lower confidence accordingly.
7. Return ONLY the JSON object. No commentary.

DOCUMENT TEXT (compressed; intro plus keyword-marked sections of the full document):
{compress_for_prompt(raw_text, budget)}"""


_FIELD_KEYS = {
    "total_vacancies",
    "min_age",
    "age_max_general",
    "age_relaxations",
    "age_cutoff_date",
    "required_qualification",
    "application_last_date",
    "pay_level",
}


def _coerce_relaxations(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, int] = {}
    for k, v in value.items():
        try:
            years = int(v)
        except (TypeError, ValueError):
            continue
        if 0 <= years <= 20:
            out[str(k).strip().upper()] = years
    return out


def _parse_llm_payload(parsed: dict) -> tuple[NotificationExtraction, str | None]:
    """Tolerant parse: accepts nested {value, confidence, evidence} envelopes
    or bare scalars (less preferred, flagged low-confidence)."""
    if not isinstance(parsed, dict):
        return NotificationExtraction(), "top-level JSON is not an object"

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
            if key == "age_relaxations":
                body[key] = _coerce_relaxations(value)
            else:
                body[key] = value
        elif key == "confidence" and isinstance(raw, (int, float)):
            body[key] = float(raw)

    try:
        extraction = NotificationExtraction.model_validate({**body, "field_confidence": field_confidence, "evidence": evidence})
    except Exception as exc:
        return NotificationExtraction(), f"schema validation failed: {exc}"

    critical_present = [f for f in CRITICAL_FIELDS if getattr(extraction, f) not in (None, "", {})]
    if critical_present:
        extraction.confidence = min(field_confidence.get(f, 0.6) for f in critical_present)
    else:
        extraction.confidence = 0.0
    return extraction, None


# ---------------------------------------------------------------------------
# Validation & flagging
# ---------------------------------------------------------------------------

def _validate_and_flag(
    result: NotificationExtraction,
    raw_chars: int,
    is_scanned: bool,
    provider: str,
) -> ExtractionResult:
    reasons: list[str] = []

    if (m := result.min_age) is not None and not 10 <= m <= 65:
        reasons.append(f"min_age {m} implausible")
    if (x := result.age_max_general) is not None and not 15 <= x <= 75:
        reasons.append(f"age_max_general {x} implausible")
    if result.min_age is not None and result.age_max_general is not None and result.min_age > result.age_max_general:
        reasons.append(f"min_age {result.min_age} > age_max_general {result.age_max_general}")
    if result.total_vacancies is not None and not 1 <= result.total_vacancies <= 500_000:
        reasons.append(f"total_vacancies {result.total_vacancies} implausible")
    for category, years in result.age_relaxations.items():
        if not re.fullmatch(r"[A-Za-z0-9&\-/ ]{1,24}", category) or years > 15:
            reasons.append(f"relaxation {category}:{years} looks wrong")

    missing = [f for f in CRITICAL_FIELDS if getattr(result, f) in (None, "", {})]
    if missing:
        reasons.append(f"missing critical fields: {', '.join(missing)}")
    if result.confidence < MIN_CONFIDENCE:
        reasons.append(f"confidence {result.confidence:.2f} below {MIN_CONFIDENCE}")

    return ExtractionResult(
        **result.model_dump(),
        raw_text_chars=raw_chars,
        is_scanned=is_scanned,
        needs_manual_review=bool(reasons) or is_scanned,
        review_reasons=reasons + (["scanned/image-only PDF — no text layer"] if is_scanned else []),
        provider=provider,
    )


# ---------------------------------------------------------------------------
# LLM calls (primary with retry, optional fallback escalation)
# ---------------------------------------------------------------------------

def _retry_after_seconds(exc: Exception, attempt: int) -> float:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) or {}
    for key in ("retry-after", "Retry-After", "x-ratelimit-reset-requests"):
        raw = headers.get(key) or headers.get(key.lower())
        if raw:
            try:
                return min(float(raw), 30.0)
            except ValueError:
                pass
    return min(2.0 * (2**attempt), 20.0)


def _retryable_status(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    return status in {408, 409, 429, 500, 502, 503, 504, 413}


async def _groq_completion(make_messages) -> str:
    """make_messages(budget) rebuilds the prompt with the current token budget.

    Retried with Retry-After-aware backoff on 429/5xx; on 413 the prompt is
    rebuilt with a 60%-smaller budget. Never waits out the limit silently.
    """
    budget = float(TOKEN_BUDGET)
    for attempt in range(MAX_ATTEMPTS):
        messages = make_messages(budget)
        try:
            response = await _groq().chat.completions.create(
                messages=messages,
                model=settings.GROQ_MODEL,
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content or "{}"
        except Exception as exc:
            if not _retryable_status(exc):
                raise
            status = getattr(exc, "status_code", None)
            if status == 413:
                budget *= 0.55
                logger.warning("prompt too large (413); rebuilding with ~%d token budget", budget)
                continue
            if attempt == MAX_ATTEMPTS - 1:
                raise
            wait = _retry_after_seconds(exc, attempt)
            logger.warning("groq attempt %d failed (status %s); retrying in %.1fs", attempt + 1, status, wait)
            await asyncio.sleep(wait)
    raise RuntimeError("unreachable")


async def _fallback_completion(messages: list[dict]) -> str | None:
    """One escalation to an OpenAI-compatible endpoint when configured."""
    if not (settings.LLM_FALLBACK_API_KEY and settings.LLM_FALLBACK_BASE_URL and settings.LLM_FALLBACK_MODEL):
        return None
    url = settings.LLM_FALLBACK_BASE_URL.rstrip("/") + "/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {settings.LLM_FALLBACK_API_KEY}"},
                json={
                    "model": settings.LLM_FALLBACK_MODEL,
                    "messages": messages,
                    "temperature": 0.0,
                    "response_format": {"type": "json_object"},
                },
            )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"] or "{}"
    except Exception as exc:
        logger.warning("fallback LLM failed: %s", exc)
        return None


async def extract_notification(pdf_bytes: bytes) -> ExtractionResult:
    text, page_count, chars_per_page = extract_text_stats(pdf_bytes)

    if chars_per_page < MIN_CHARS_PER_PAGE:
        logger.info("notification PDF looks scanned (%.0f chars/page over %d pages)", chars_per_page, page_count)
        return ExtractionResult(
            confidence=0.0,
            raw_text_chars=len(text),
            is_scanned=True,
            needs_manual_review=True,
            review_reasons=[f"scanned/image-only PDF — {chars_per_page:.0f} chars/page, no usable text layer"],
        )

    cleaned = clean_raw_text(text)

    def make_messages(budget: float) -> list[dict]:
        return [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_prompt(cleaned, budget)},
        ]

    messages = make_messages(float(TOKEN_BUDGET))
    try:
        raw = await _groq_completion(make_messages)
    except Exception as exc:
        logger.warning("primary LLM failed after retries: %s — trying fallback", exc)
        raw = await _fallback_completion(messages)
        if raw is None:
            return ExtractionResult(
                confidence=0.0,
                raw_text_chars=len(cleaned),
                needs_manual_review=True,
                review_reasons=[f"LLM unavailable: {exc}"],
                provider="unavailable",
            )

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("LLM output is not JSON: %s", exc)
        parsed = {}

    extraction, parse_error = _parse_llm_payload(parsed)
    provider = "groq"

    # Escalate to the fallback provider once when the primary underperforms.
    needs_review = bool(parse_error) or any(
        getattr(extraction, f) in (None, "", {}) for f in CRITICAL_FIELDS
    ) or extraction.confidence < MIN_CONFIDENCE
    if needs_review:
        fallback_raw = await _fallback_completion(messages)
        if fallback_raw:
            try:
                fallback_parsed = json.loads(fallback_raw)
                fallback_extraction, fallback_error = _parse_llm_payload(fallback_parsed)
                if not fallback_error and (
                    fallback_extraction.confidence > extraction.confidence
                    or all(getattr(fallback_extraction, f) not in (None, "", {}) for f in CRITICAL_FIELDS)
                ):
                    extraction, parse_error, provider = fallback_extraction, None, "fallback"
            except json.JSONDecodeError:
                pass

    if parse_error:
        return ExtractionResult(
            confidence=0.0,
            raw_text_chars=len(cleaned),
            needs_manual_review=True,
            review_reasons=[f"LLM output unparseable/invalid: {parse_error}"],
            provider=provider,
        )

    return _validate_and_flag(extraction, raw_chars=len(cleaned), is_scanned=False, provider=provider)
