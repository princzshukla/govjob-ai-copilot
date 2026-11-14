# app/schemas/pipeline.py
"""Schemas for the Layer 2 notification-extraction pipeline."""
from datetime import date

from pydantic import BaseModel, Field


class NotificationExtraction(BaseModel):
    """LLM-extracted fields from a government recruitment notification PDF.

    Age is modelled the way statutory reservation actually works: a base
    (general-category) limit plus per-category relaxations. The eligibility
    engine computes the per-user result from these two — it must never hard
    -code a single upper age.
    """

    total_vacancies: int | None = None
    min_age: int | None = None
    age_max_general: int | None = None
    # e.g. {"OBC": 3, "SC": 5, "ST": 5, "PwBD": 10} — years relaxed over the
    # general limit, as stated in the notification (falls back to statutory
    # defaults in the matcher when the dict is empty).
    age_relaxations: dict[str, int] = Field(default_factory=dict)
    age_cutoff_date: date | None = None
    required_qualification: str | None = Field(
        default=None,
        description="Degree + stream, e.g. 'B.Tech (Computer Science / IT)'",
    )
    application_last_date: date | None = None
    pay_level: str | None = Field(
        default=None,
        description="Pay level / scale / salary as written, e.g. 'Level 4 (₹25,500 - ₹81,100)'",
    )
    # Per-field confidence (0..1) and exact-quote evidence snippets.
    field_confidence: dict[str, float] = Field(default_factory=dict)
    evidence: dict[str, str] = Field(default_factory=dict)
    # Overall confidence — the minimum over present critical fields.
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ExtractionResult(NotificationExtraction):
    """Extraction output plus the pipeline's trust decision."""

    raw_text_chars: int = 0
    is_scanned: bool = False
    needs_manual_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)
    provider: str = "groq"


class BenchmarkPdfEntry(BaseModel):
    file: str
    source: str
    url: str
    expected: dict[str, object]
    notes: str | None = None
