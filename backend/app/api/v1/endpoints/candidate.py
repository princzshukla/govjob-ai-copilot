# app/api/v1/endpoints/candidate.py
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import optional_current_user, user_or_ip_key
from app.api.v1.endpoints.eligibility import DEFAULT_TOPICS, _ensure_seed_exams
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.auth import User
from app.models.candidate import CandidateProfile
from app.schemas.candidate import (
    CandidateProfileCreate,
    CandidateProfileResponse,
    ResumeParseResponse,
)
from app.schemas.exam import EligibilityCheckResponse
from app.services.matcher import evaluate_all_exams
from app.services.parser import extract_raw_text_from_pdf, parse_resume_with_groq

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/candidate", tags=["Candidate"])

MAX_RESUME_BYTES = 5 * 1024 * 1024  # 5 MB
PDF_MAGIC = b"%PDF-"
ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}


def _resume_upload_limit(key: str) -> str:
    """Per-account quota for signed-in users, tighter per-IP quota for guests."""
    return "20/day" if key.startswith("user:") else "3/day"


def _ensure_profile_access(profile: CandidateProfile, user: User | None) -> None:
    """404s when an owned profile is requested by anyone but its owner.

    Guest (unowned) profiles stay reachable by their unguessable id. The 404,
    rather than 403, avoids confirming that a profile id exists.
    """
    if profile.user_id is not None and (user is None or user.id != profile.user_id):
        raise HTTPException(status_code=404, detail="Candidate profile not found")


@router.post("/parse-resume", response_model=ResumeParseResponse)
@limiter.limit(_resume_upload_limit, key_func=user_or_ip_key)
async def upload_and_parse_resume(
    request: Request,
    file: UploadFile = File(...),
    _user: User | None = Depends(optional_current_user),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF resume uploads are currently supported.",
        )

    # Read at most one byte past the cap, so an oversized upload is rejected
    # without buffering the whole body.
    pdf_bytes = await file.read(MAX_RESUME_BYTES + 1)
    if len(pdf_bytes) > MAX_RESUME_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Resume file must be 5 MB or smaller.",
        )

    # Content-Type is client supplied; the PDF signature is not.
    if not pdf_bytes.startswith(PDF_MAGIC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF resume uploads are currently supported.",
        )

    try:
        raw_text = extract_raw_text_from_pdf(pdf_bytes)
    except Exception:
        logger.exception("Failed to extract text from uploaded resume")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not read the PDF file.",
        )

    if not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract text from PDF. It may be scanned or image-only.",
        )

    try:
        return await parse_resume_with_groq(raw_text)
    except HTTPException:
        raise
    except Exception:
        # Never echo exception text: it can leak prompts, keys or internal paths.
        logger.exception("Resume parsing failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Resume parsing failed. Please try again later.",
        )


@router.post("/profile", status_code=status.HTTP_201_CREATED)
async def save_candidate_profile(
    payload: CandidateProfileCreate,
    profile_id: Optional[str] = Query(
        default=None,
        description="Pass an existing profile_id to update instead of creating a new record",
    ),
    user: User | None = Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Persists a manual or resume-parsed CandidateProfile to PostgreSQL.
    Returns the profile_id so the frontend can store it and re-run matches anytime.
    Signed-in callers own the profile; guests get an anonymous profile that is
    reachable only by its unguessable id.
    """
    data = payload.model_dump()

    if profile_id:
        res = await db.execute(
            select(CandidateProfile).where(CandidateProfile.id == profile_id)
        )
        existing = res.scalar_one_or_none()
        if existing:
            _ensure_profile_access(existing, user)
            for key, value in data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            if user is not None and existing.user_id is None:
                # Adopt the guest profile into the caller's account.
                existing.user_id = user.id
            await db.commit()
            await db.refresh(existing)
            return {
                "profile_id": existing.id,
                "status": "updated",
                "profile": data,
            }

    new_id = profile_id or str(uuid.uuid4())
    valid_cols = {c.key for c in CandidateProfile.__table__.columns}
    filtered_data = {k: v for k, v in data.items() if k in valid_cols}

    candidate = CandidateProfile(
        id=new_id,
        user_id=user.id if user is not None else None,
        **filtered_data,
    )
    db.add(candidate)
    await db.commit()
    await db.refresh(candidate)

    return {
        "profile_id": candidate.id,
        "status": "created",
        "profile": data,
    }


@router.get("/profile/{profile_id}", response_model=CandidateProfileResponse)
async def get_candidate_profile(
    profile_id: str,
    user: User | None = Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetches a persisted candidate profile from PostgreSQL."""
    res = await db.execute(
        select(CandidateProfile).where(CandidateProfile.id == profile_id)
    )
    candidate = res.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found")

    _ensure_profile_access(candidate, user)

    return CandidateProfileResponse(
        profile_id=candidate.id,
        full_name=candidate.full_name,
        dob=candidate.dob,
        gender=candidate.gender,
        category=candidate.category,
        is_pwd=candidate.is_pwd,
        domicile_state=candidate.domicile_state,
        highest_degree=candidate.highest_degree,
        stream=candidate.stream,
        percentage_cgpa=float(candidate.percentage_cgpa)
        if candidate.percentage_cgpa is not None
        else 0.0,
        passing_year=candidate.passing_year,
        graduation_status=candidate.graduation_status or "Completed",
        previous_attempts=candidate.previous_attempts or 0,
        skills=candidate.skills or [],
        raw_resume_text=candidate.raw_resume_text,
    )


@router.get("/profile/{profile_id}/eligibility", response_model=EligibilityCheckResponse)
async def check_saved_profile_eligibility(
    profile_id: str,
    primary_exam_id: Optional[str] = Query(
        default="ssc-cgl-general",
        description="Exam ID used to calculate Plan-B syllabus overlap percentages",
    ),
    user: User | None = Depends(optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Loads a saved CandidateProfile from PostgreSQL and evaluates eligibility
    against all active government exams.
    """
    res = await db.execute(
        select(CandidateProfile).where(CandidateProfile.id == profile_id)
    )
    candidate_row = res.scalar_one_or_none()
    if not candidate_row:
        raise HTTPException(status_code=404, detail="Candidate profile not found")

    _ensure_profile_access(candidate_row, user)

    profile_schema = CandidateProfileCreate(
        full_name=candidate_row.full_name,
        dob=candidate_row.dob,
        gender=candidate_row.gender,
        category=candidate_row.category,
        is_pwd=candidate_row.is_pwd,
        domicile_state=candidate_row.domicile_state,
        highest_degree=candidate_row.highest_degree,
        stream=candidate_row.stream,
        percentage_cgpa=float(candidate_row.percentage_cgpa)
        if candidate_row.percentage_cgpa is not None
        else 0.0,
        passing_year=candidate_row.passing_year,
        graduation_status=candidate_row.graduation_status or "Completed",
        previous_attempts=candidate_row.previous_attempts or 0,
        skills=candidate_row.skills or [],
        raw_resume_text=candidate_row.raw_resume_text,
    )

    exams = await _ensure_seed_exams(db)
    exam_topics_map = {
        exam.id: set(exam.topics or DEFAULT_TOPICS) for exam in exams
    }

    return evaluate_all_exams(
        candidate=profile_schema,
        exams=exams,
        exam_topics_map=exam_topics_map,
        primary_exam_id=primary_exam_id,
    )
