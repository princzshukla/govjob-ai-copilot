from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.schemas.candidate import CandidateProfileCreate
from app.schemas.exam import EligibilityCheckResponse
from app.schemas.roadmap import StudyRoadmapResponse
from app.models.exam import ExamNotification
from app.core.seed import SEED_EXAMS
from app.services.matcher import evaluate_all_exams
from app.services.roadmap_generator import generate_study_roadmap_groq

router = APIRouter(prefix="/eligibility", tags=["Eligibility & Roadmaps"])

# Add at the top of backend/app/api/v1/endpoints/eligibility.py
ROADMAP_CACHE: dict[str, StudyRoadmapResponse] = {}

@router.post("/generate-roadmap/{exam_id}", response_model=StudyRoadmapResponse)
async def create_exam_roadmap(
    exam_id: str,
    target_weeks: int = Query(default=12, ge=4, le=52)
):
    cache_key = f"{exam_id}_{target_weeks}"
    if cache_key in ROADMAP_CACHE:
        return ROADMAP_CACHE[cache_key]

    exam_obj = next((e for e in EXAM_MODELS if e.id == exam_id), None)
    if not exam_obj:
        raise HTTPException(status_code=404, detail="Exam ID not found")

    topics = list(EXAM_TOPICS_MAP.get(exam_id, []))
    roadmap = await generate_study_roadmap_groq(
        exam_title=exam_obj.title,
        syllabus_topics=topics,
        target_weeks=target_weeks
    )
    ROADMAP_CACHE[cache_key] = roadmap
    return roadmap  

# Convert seed dicts into model objects & topic maps for immediate testing
EXAM_MODELS = [
    ExamNotification(**{k: v for k, v in item.items() if k != "topics"})
    for item in SEED_EXAMS
]
EXAM_TOPICS_MAP = {item["id"]: item["topics"] for item in SEED_EXAMS}

@router.post("/check", response_model=EligibilityCheckResponse)
async def check_candidate_eligibility(
    profile: CandidateProfileCreate,
    primary_exam_id: Optional[str] = Query(
        default="ssc-cgl-general",
        description="Exam ID used to calculate Plan-B syllabus overlap percentages"
    )
):
    """
    Evaluates a parsed resume or manual candidate profile against all government exams
    and computes syllabus overlap with the primary target exam.
    """
    return evaluate_all_exams(
        candidate=profile,
        exams=EXAM_MODELS,
        exam_topics_map=EXAM_TOPICS_MAP,
        primary_exam_id=primary_exam_id
    )

@router.post("/generate-roadmap/{exam_id}", response_model=StudyRoadmapResponse)
async def create_exam_roadmap(
    exam_id: str,
    target_weeks: int = Query(default=12, ge=4, le=52)
):
    """
    Generates an AI-structured week-by-week preparation roadmap using Groq
    for the chosen eligible exam.
    """
    exam_obj = next((e for e in EXAM_MODELS if e.id == exam_id), None)
    if not exam_obj:
        raise HTTPException(status_code=404, detail="Exam ID not found")

    topics = list(EXAM_TOPICS_MAP.get(exam_id, []))
    return await generate_study_roadmap_groq(
        exam_title=exam_obj.title,
        syllabus_topics=topics,
        target_weeks=target_weeks
    )
@router.post("/sync-live-jobs")
async def sync_live_government_jobs():
    """
    Scrapes live government notifications from the web, structures them via Groq,
    and appends them to the active EXAM_MODELS list.
    """
    from app.services.job_scraper import fetch_raw_job_listings, structure_jobs_with_groq
    from datetime import date as dt_date
    from app.models.exam import ExamNotification

    try:
        raw_listings = await fetch_raw_job_listings()
        structured_list = await structure_jobs_with_groq(raw_listings)

        added_count = 0
        existing_ids = {e.id for e in EXAM_MODELS}

        for item in structured_list:
            if item["id"] not in existing_ids:
                topics = set(item.pop("topics", ["General Intelligence", "Quantitative Aptitude", "Current Affairs"]))
                item["application_deadline"] = dt_date.fromisoformat(item["application_deadline"])
                item["age_cutoff_date"] = dt_date.fromisoformat(item["age_cutoff_date"])
                if item.get("exam_date"):
                    item["exam_date"] = dt_date.fromisoformat(item["exam_date"])

                EXAM_MODELS.append(ExamNotification(**item))
                EXAM_TOPICS_MAP[item["id"]] = topics
                added_count += 1

        return {
            "status": "success",
            "new_jobs_discovered": added_count,
            "total_active_jobs": len(EXAM_MODELS)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "total_active_jobs": len(EXAM_MODELS)
        }