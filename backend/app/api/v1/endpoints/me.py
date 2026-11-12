# app/api/v1/endpoints/me.py
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import current_user, user_or_ip_key
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.auth import User
from app.models.candidate import CandidateProfile
from app.models.progress import RoadmapProgress
from app.models.roadmap import SavedRoadmap
from app.schemas.me import (
    CandidateProfileIn,
    CandidateProfileOut,
    ClaimDraftIn,
    ClaimDraftOut,
    ProgressOut,
    RoadmapConcreteOut,
    WeekDoneIn,
)
from app.schemas.roadmap import StudyRoadmapResponse
from app.services.roadmap_store import (
    get_completed_weeks,
    progress_payload,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/me", tags=["Me"])

ROADMAP_NOT_FOUND = "Roadmap not found"

# Columns whose DB defaults must be filled whenever a payload sends null;
# they must never be inserted as NULL.
_DEFAULTED_FIELDS = {"gender": "Male", "category": "General"}


def _profile_out(row: CandidateProfile) -> CandidateProfileOut:
    return CandidateProfileOut(
        id=row.id,
        full_name=row.full_name,
        dob=row.dob,
        gender=row.gender,
        category=row.category,
        is_pwd=row.is_pwd,
        domicile_state=row.domicile_state,
        highest_degree=row.highest_degree,
        stream=row.stream,
        percentage_cgpa=float(row.percentage_cgpa) if row.percentage_cgpa is not None else None,
        passing_year=row.passing_year,
        skills=list(row.skills or []),
    )


def _profile_values(payload: CandidateProfileIn) -> dict:
    values = payload.model_dump()
    for field, default in _DEFAULTED_FIELDS.items():
        if values.get(field) is None:
            values[field] = default
    if values.get("is_pwd") is None:
        values["is_pwd"] = False
    return values


async def _get_profile_row(db: AsyncSession, user_id: int) -> CandidateProfile | None:
    return await db.scalar(
        select(CandidateProfile).where(CandidateProfile.user_id == user_id)
    )


async def _get_owned_roadmap(
    db: AsyncSession, user_id: int, roadmap_id: str
) -> SavedRoadmap:
    roadmap = await db.get(SavedRoadmap, roadmap_id)
    # Existence and ownership failure look identical (404): never leak which id
    # exists.
    if roadmap is None or roadmap.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ROADMAP_NOT_FOUND)
    return roadmap


# ------------------------------------------------------------- Profile

@router.get("/profile", response_model=CandidateProfileOut)
async def get_profile(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateProfileOut:
    row = await _get_profile_row(db, user.id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No profile saved yet"
        )
    return _profile_out(row)


@router.put("/profile", response_model=CandidateProfileOut)
@limiter.limit("30/minute", key_func=user_or_ip_key)
async def put_profile(
    request: Request,
    payload: CandidateProfileIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateProfileOut:
    """Full replace: the account stores exactly this profile.

    Missing optional fields are stored as missing (partial drafts are a normal
    state), except the defaulted columns above, which never become NULL.
    """
    values = _profile_values(payload)
    row = await _get_profile_row(db, user.id)
    if row is None:
        row = CandidateProfile(id=str(uuid.uuid4()), user_id=user.id, **values)
        db.add(row)
    else:
        for key, value in values.items():
            setattr(row, key, value)
    await db.commit()
    return _profile_out(row)


# ------------------------------------------------------------ Roadmaps

@router.get("/roadmaps/{exam_id}", response_model=RoadmapConcreteOut)
async def get_roadmap(
    exam_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> RoadmapConcreteOut:
    row = await db.scalar(
        select(SavedRoadmap).where(
            SavedRoadmap.user_id == user.id,
            SavedRoadmap.exam_id == exam_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ROADMAP_NOT_FOUND)

    completed = await get_completed_weeks(db, row.id)
    progress = progress_payload(row.id, row.target_weeks, completed)
    return RoadmapConcreteOut(
        exam_id=row.exam_id,
        roadmap=StudyRoadmapResponse.model_validate(row.roadmap_json),
        created_at=row.created_at,
        **progress,
    )


@router.get("/roadmaps/{roadmap_id}/progress", response_model=ProgressOut)
async def get_progress(
    roadmap_id: str,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> ProgressOut:
    roadmap = await _get_owned_roadmap(db, user.id, roadmap_id)
    completed = await get_completed_weeks(db, roadmap.id)
    return ProgressOut(**progress_payload(roadmap.id, roadmap.target_weeks, completed))


@router.put("/roadmaps/{roadmap_id}/weeks/{week_no}", response_model=ProgressOut)
@limiter.limit("120/minute", key_func=user_or_ip_key)
async def set_week_done(
    request: Request,
    roadmap_id: str,
    week_no: int,
    payload: WeekDoneIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> ProgressOut:
    roadmap = await _get_owned_roadmap(db, user.id, roadmap_id)

    if week_no < 1 or week_no > roadmap.target_weeks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"week_no must be between 1 and {roadmap.target_weeks}",
        )

    if payload.done:
        # Idempotent insert; a repeat tap cannot create a duplicate row.
        stmt = pg_insert(RoadmapProgress).values(roadmap_id=roadmap.id, week_no=week_no)
        stmt = stmt.on_conflict_do_nothing()
        await db.execute(stmt)
    else:
        await db.execute(
            delete(RoadmapProgress).where(
                RoadmapProgress.roadmap_id == roadmap.id,
                RoadmapProgress.week_no == week_no,
            )
        )
    await db.commit()

    completed = await get_completed_weeks(db, roadmap.id)
    return ProgressOut(**progress_payload(roadmap.id, roadmap.target_weeks, completed))


# ------------------------------------------------------------ Draft claim

@router.post("/claim-draft", response_model=ClaimDraftOut)
@limiter.limit("10/minute", key_func=user_or_ip_key)
async def claim_draft(
    request: Request,
    payload: ClaimDraftIn,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> ClaimDraftOut:
    """Attach a guest's parsed/completed draft to the signed-in user — once.

    Idempotent: if the account already has a profile the draft is not merged
    or overwritten; the existing profile is returned with ``already_claimed``.

    The uploaded draft is validated and size-capped, but is never used as the
    source of truth for anything else (and raw resume text is never stored).
    """
    existing = await _get_profile_row(db, user.id)
    if existing is not None:
        return ClaimDraftOut(status="already_claimed", profile=_profile_out(existing))

    values = _profile_values(payload)
    row = CandidateProfile(
        id=str(uuid.uuid4()),
        user_id=user.id,
        **values,
    )
    db.add(row)
    try:
        await db.commit()
    except IntegrityError:
        # Concurrent claim or a legacy race; the profile already exists.
        await db.rollback()
        row = await _get_profile_row(db, user.id)
        assert row is not None
        return ClaimDraftOut(status="already_claimed", profile=_profile_out(row))
    return ClaimDraftOut(status="claimed", profile=_profile_out(row))
