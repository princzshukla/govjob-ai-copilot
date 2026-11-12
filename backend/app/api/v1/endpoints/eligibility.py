import logging
import time
from datetime import date as dt_date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.v1.deps import current_user, user_or_ip_key
from app.core.rate_limit import limiter
from app.core.seed import SEED_EXAMS
from app.models.auth import User
from app.models.exam import ExamNotification
from app.schemas.candidate import CandidateProfileCreate
from app.schemas.exam import EligibilityCheckResponse
from app.schemas.roadmap import StudyRoadmapResponse
from app.services.matcher import evaluate_all_exams
from app.services.roadmap_generator import generate_study_roadmap_groq

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/eligibility", tags=["Eligibility & Roadmaps"])

# In-memory cache for generated roadmaps, keyed by "exam_id_target_weeks".
ROADMAP_CACHE: dict[str, StudyRoadmapResponse] = {}

# Convert seed dicts into model objects & topic maps for immediate testing.
EXAM_MODELS = [
    ExamNotification(**{k: v for k, v in item.items() if k != "topics"})
    for item in SEED_EXAMS
]
EXAM_TOPICS_MAP = {item["id"]: set(item["topics"]) for item in SEED_EXAMS}

DEFAULT_TOPICS = ["General Intelligence", "Quantitative Aptitude", "Current Affairs"]

# Server-wide cooldown for the expensive scrape + LLM sync. Shared by every
# caller, because the cost is global, not per user.
SYNC_COOLDOWN_SECONDS = 15 * 60
_last_sync_started_at: float | None = None


@router.post("/generate-roadmap/{exam_id}", response_model=StudyRoadmapResponse)
@limiter.limit("10/hour", key_func=user_or_ip_key)
async def create_exam_roadmap(
    request: Request,
    exam_id: str,
    target_weeks: int = Query(default=12, ge=4, le=52),
    user: User = Depends(current_user),
):
    """
    Generates an AI-structured week-by-week preparation roadmap using Groq
    for the chosen eligible exam. Results are cached per exam/duration so the
    same roadmap is not paid for twice.
    """
    cache_key = f"{exam_id}_{target_weeks}"
    if cache_key in ROADMAP_CACHE:
        return ROADMAP_CACHE[cache_key]

    exam_obj = next((e for e in EXAM_MODELS if e.id == exam_id), None)
    if not exam_obj:
        raise HTTPException(status_code=404, detail="Exam ID not found")

    topics = list(EXAM_TOPICS_MAP.get(exam_id, ()))

    roadmap = await generate_study_roadmap_groq(
        exam_title=exam_obj.title,
        syllabus_topics=topics,
        target_weeks=target_weeks
    )
    ROADMAP_CACHE[cache_key] = roadmap
    return roadmap


@router.post("/check", response_model=EligibilityCheckResponse)
@limiter.limit("30/hour")
async def check_candidate_eligibility(
    request: Request,
    profile: CandidateProfileCreate,
    primary_exam_id: Optional[str] = Query(
        default="ssc-cgl-general",
        description="Exam ID used to calculate Plan-B syllabus overlap percentages"
    )
):
    """
    Evaluates a parsed resume or manual candidate profile against all government exams
    and computes syllabus overlap with the primary target exam.

    Guests may use this, so the limit is per IP.
    """
    return evaluate_all_exams(
        candidate=profile,
        exams=EXAM_MODELS,
        exam_topics_map=EXAM_TOPICS_MAP,
        primary_exam_id=primary_exam_id
    )


@router.post("/sync-live-jobs")
@limiter.limit("4/hour", key_func=user_or_ip_key)
async def sync_live_government_jobs(
    request: Request,
    user: User = Depends(current_user),
):
    """
    Scrapes live government notifications from the web, structures them via Groq,
    and appends them to the active EXAM_MODELS list.

    Requires login and is globally throttled, because one call costs a scrape
    plus LLM work for everybody.
    """
    global _last_sync_started_at

    now = time.monotonic()
    if _last_sync_started_at is not None:
        elapsed = now - _last_sync_started_at
        if elapsed < SYNC_COOLDOWN_SECONDS:
            retry_after = int(SYNC_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(
                status_code=429,
                detail="Live job sync was run recently. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )
    _last_sync_started_at = now

    from app.services.job_scraper import fetch_raw_job_listings, structure_jobs_with_groq

    try:
        raw_listings = await fetch_raw_job_listings()
        structured_list = await structure_jobs_with_groq(raw_listings)
    except Exception:
        # Do not reflect scraper/LLM exception text back to clients.
        logger.exception("Live job sync failed")
        raise HTTPException(
            status_code=502,
            detail="Live job sync failed. Please try again later.",
        )

    existing_ids = {e.id for e in EXAM_MODELS}
    added_count = 0
    skipped_count = 0

    for item in structured_list:
        if item.get("id") in existing_ids:
            skipped_count += 1
            continue

        try:
            topics = set(item.pop("topics", DEFAULT_TOPICS))
            item["application_deadline"] = dt_date.fromisoformat(item["application_deadline"])
            item["age_cutoff_date"] = dt_date.fromisoformat(item["age_cutoff_date"])
            if item.get("exam_date"):
                item["exam_date"] = dt_date.fromisoformat(item["exam_date"])

            exam = ExamNotification(**item)
        except (KeyError, TypeError, ValueError):
            # A single malformed record from the LLM must not discard the
            # whole batch.
            skipped_count += 1
            continue

        EXAM_MODELS.append(exam)
        EXAM_TOPICS_MAP[item["id"]] = topics
        existing_ids.add(item["id"])
        added_count += 1

    return {
        "status": "success",
        "new_jobs_discovered": added_count,
        "skipped_jobs": skipped_count,
        "total_active_jobs": len(EXAM_MODELS)
    }
