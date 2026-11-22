import logging
import time
import uuid
from collections import OrderedDict
from datetime import date as dt_date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import current_user, user_or_ip_key
from app.core.rate_limit import limiter
from app.core.seed import SEED_EXAMS
from app.core.seo import id_prefix_from_slug
from app.core.timeutils import today_ist
from app.core.database import get_db
from app.models.auth import User
from app.models.exam import ExamNotification
from app.models.report import EligibilityReport
from app.schemas.candidate import CandidateProfileCreate
from app.schemas.exam import (
    EligibilityCheckResponse,
    EligibilityReportCreate,
    EligibilityReportResponse,
)
from app.schemas.roadmap import StudyRoadmapResponse
from app.services.matcher import evaluate_all_exams
from app.services.roadmap_generator import generate_study_roadmap_groq
from app.services.roadmap_store import upsert_saved_roadmap

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/eligibility", tags=["Eligibility & Roadmaps"])

# In-memory cache for generated roadmaps, keyed by "exam_id_target_weeks".
# Bounded so a crawler walking exam/week combinations cannot grow it forever.
ROADMAP_CACHE: OrderedDict[str, StudyRoadmapResponse] = OrderedDict()
ROADMAP_CACHE_MAX = 256

DEFAULT_TOPICS = ["General Intelligence", "Quantitative Aptitude", "Current Affairs"]

# Server-wide cooldown for the expensive scrape + LLM sync. Shared by every
# caller, because the cost is global, not per user.
SYNC_COOLDOWN_SECONDS = 15 * 60
_last_sync_started_at: float | None = None


async def _seed_and_backfill(db: AsyncSession) -> None:
    """Insert missing SEED_EXAMS rows (first run) and backfill provenance.

    Runs over every row — open or closed — so closed rows also get their
    `source_url`/`last_checked_at` backfilled. Never overwrites anything.
    """
    count_result = await db.execute(select(func.count()).select_from(ExamNotification))
    total = count_result.scalar_one()

    if total == 0:
        for item in SEED_EXAMS:
            payload = {
                k: (list(v) if k == "topics" else v)
                for k, v in item.items()
            }
            db.add(ExamNotification(**payload))
        await db.commit()

    # Backfill provenance for rows seeded before T7. `last_checked_at` means the
    # day this API last verified the stored notification, not a re-scrape.
    # Only load rows that still need backfilling. The previous full-table
    # SELECT ran on every /exams and /check request, which crawlers hammer.
    result = await db.execute(
        select(ExamNotification).where(
            or_(
                ExamNotification.source_url.is_(None),
                ExamNotification.last_checked_at.is_(None),
            )
        )
    )
    metadata_changed = False
    for exam in result.scalars().all():
        if not exam.source_url:
            exam.source_url = exam.official_pdf_url
            metadata_changed = True
        if not exam.last_checked_at:
            exam.last_checked_at = dt_date.today()
            metadata_changed = True
    if metadata_changed:
        await db.commit()


async def _ensure_seed_exams(db: AsyncSession) -> list[ExamNotification]:
    """Seeds SEED_EXAMS into PostgreSQL on first run, then returns open exams."""
    await _seed_and_backfill(db)

    # Query-time backstop: even if the scheduled expiry job misses a run,
    # closed jobs are never presented as open. Deadlines are IST calendar
    # dates, valid through end-of-day; a missing deadline stays visible
    # (rendered as "check official notification").
    result = await db.execute(
        select(ExamNotification).where(
            ExamNotification.is_active.is_(True),
            or_(
                ExamNotification.application_deadline.is_(None),
                ExamNotification.application_deadline >= today_ist(),
            ),
        )
    )
    return list(result.scalars().all())


def _exam_list_item(exam: ExamNotification) -> dict:
    """Serialize one exam row for the listing API (all columns + window state)."""
    today = today_ist()
    if exam.application_deadline is None:
        state = "unknown"
    elif exam.application_deadline >= today:
        state = "open"
    else:
        state = "closed"
    item = {c.name: getattr(exam, c.name) for c in ExamNotification.__table__.columns}
    item["window_state"] = state
    return item


@router.get("/exams")
async def list_active_exams(
    response: Response,
    status: str = Query(default="open", pattern="^(open|all)$"),
    db: AsyncSession = Depends(get_db),
):
    """Lists government exam notifications stored in PostgreSQL.

    ``status=open`` (default) returns only exams whose window is open —
    ``is_active`` and deadline not past (IST). ``status=all`` returns every
    stored notification, including closed cycles, each annotated with a
    computed ``window_state`` (``open`` | ``closed`` | ``unknown``) so clients
    can show honest apply/closed states.
    """
    await _seed_and_backfill(db)
    stmt = select(ExamNotification)
    if status == "open":
        stmt = stmt.where(
            ExamNotification.is_active.is_(True),
            or_(
                ExamNotification.application_deadline.is_(None),
                ExamNotification.application_deadline >= today_ist(),
            ),
        )
    exams = list((await db.execute(stmt)).scalars().all())

    if status == "all":
        open_rows = [e for e in exams if _exam_list_item(e)["window_state"] != "closed"]
        closed_rows = [e for e in exams if _exam_list_item(e)["window_state"] == "closed"]
        open_rows.sort(key=lambda e: (e.application_deadline is None, e.application_deadline or dt_date.max))
        closed_rows.sort(key=lambda e: e.application_deadline or dt_date.min, reverse=True)
        exams = open_rows + closed_rows
    response.headers["Cache-Control"] = "public, s-maxage=300, stale-while-revalidate=600"
    return {"total": len(exams), "exams": [_exam_list_item(e) for e in exams]}


@router.get("/exams/{key}")
async def get_exam_by_key(
    key: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """One notification by its public URL key. Closed cycles are returned too."""
    prefix = id_prefix_from_slug(key)
    if prefix is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    normalised_id = func.replace(
        func.replace(func.lower(ExamNotification.id), "-", ""), "_", ""
    )
    row = (
        await db.execute(select(ExamNotification).where(normalised_id == prefix))
    ).scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    response.headers["Cache-Control"] = "public, s-maxage=300, stale-while-revalidate=600"
    return _exam_list_item(row)


@router.post("/generate-roadmap/{exam_id}", response_model=StudyRoadmapResponse)
@limiter.limit("10/hour", key_func=user_or_ip_key)
async def create_exam_roadmap(
    request: Request,
    exam_id: str,
    target_weeks: int = Query(default=12, ge=4, le=52),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates an AI-structured week-by-week preparation roadmap using Groq
    for the chosen eligible exam. Results are cached per exam/duration so the
    same roadmap is not paid for twice. Either way, the roadmap is also saved
    against the session user so it survives across devices and refreshes.
    """
    cache_key = f"{exam_id}_{target_weeks}"
    if cache_key in ROADMAP_CACHE:
        roadmap = ROADMAP_CACHE[cache_key]
        ROADMAP_CACHE.move_to_end(cache_key)
    else:
        # A roadmap is a study plan built from the exam's syllabus — it is not
        # an application action, so a closed application window must not make
        # the exam unfindable. Seed if needed, then look the row up by id only.
        await _seed_and_backfill(db)
        exam_obj = (
            await db.execute(
                select(ExamNotification).where(ExamNotification.id == exam_id)
            )
        ).scalar_one_or_none()
        if not exam_obj:
            raise HTTPException(status_code=404, detail="Exam ID not found")

        topics = list(exam_obj.topics or DEFAULT_TOPICS)

        roadmap = await generate_study_roadmap_groq(
            exam_title=exam_obj.title,
            syllabus_topics=topics,
            target_weeks=target_weeks
        )
        ROADMAP_CACHE[cache_key] = roadmap
        if len(ROADMAP_CACHE) > ROADMAP_CACHE_MAX:
            ROADMAP_CACHE.popitem(last=False)

    await upsert_saved_roadmap(
        db,
        user_id=user.id,
        exam_id=exam_id,
        target_weeks=target_weeks,
        roadmap=roadmap,
    )
    return roadmap


@router.post("/check", response_model=EligibilityCheckResponse)
@limiter.limit("30/hour")
async def check_candidate_eligibility(
    request: Request,
    profile: CandidateProfileCreate,
    primary_exam_id: Optional[str] = Query(
        default="ssc-cgl-general",
        description="Exam ID used to calculate Plan-B syllabus overlap percentages",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluates a parsed resume or manual candidate profile against all active
    PostgreSQL exam notifications and computes Plan-B syllabus overlap percentages.

    Guests may use this, so the limit is per IP.
    """
    exams = await _ensure_seed_exams(db)
    exam_topics_map = {
        exam.id: set(exam.topics or DEFAULT_TOPICS) for exam in exams
    }

    return evaluate_all_exams(
        candidate=profile,
        exams=exams,
        exam_topics_map=exam_topics_map,
        primary_exam_id=primary_exam_id,
    )


@router.post(
    "/report",
    response_model=EligibilityReportResponse,
    status_code=201,
)
@limiter.limit("5/hour")
async def report_wrong_eligibility_result(
    request: Request,
    payload: EligibilityReportCreate,
    db: AsyncSession = Depends(get_db),
):
    """Saves a "report wrong result" submission.

    The candidate snapshot intentionally drops the name and raw resume text, so
    reports never store contact-style free text. The exam is stored by id plus a
    small snapshot of its provenance for later review.
    """
    await _ensure_seed_exams(db)

    exam_res = await db.execute(
        select(ExamNotification).where(ExamNotification.id == payload.exam_id)
    )
    exam = exam_res.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam ID not found")

    candidate_snapshot = payload.candidate.model_dump(
        mode="json",
        exclude={"full_name", "raw_resume_text"},
    )
    exam_snapshot = {
        "exam_id": exam.id,
        "title": exam.title,
        "organizing_body": exam.organizing_body,
        "post_type": exam.post_type,
        "application_deadline": (
            exam.application_deadline.isoformat() if exam.application_deadline else None
        ),
        "source_url": exam.source_url or exam.official_pdf_url,
        "apply_url": exam.apply_url,
        "last_checked_at": (
            exam.last_checked_at or dt_date.today()
        ).isoformat(),
    }

    created_at = datetime.now(timezone.utc)
    report = EligibilityReport(
        id=str(uuid.uuid4()),
        exam_id=exam.id,
        reported_verdict=payload.reported_verdict,
        expected_verdict=payload.expected_verdict,
        candidate_snapshot=candidate_snapshot,
        exam_snapshot=exam_snapshot,
        note=payload.note,
        created_at=created_at,
    )
    db.add(report)
    await db.commit()

    return EligibilityReportResponse(
        report_id=report.id,
        status="received",
        exam_id=exam.id,
        created_at=created_at,
    )


@router.post("/sync-live-jobs")
@limiter.limit("4/hour", key_func=user_or_ip_key)
async def sync_live_government_jobs(
    request: Request,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Discover new notifications from the official pipeline sources.

    Runs one Layer-1 discovery pass over the official tier-1 sources
    (UPSC What's New, SSC Notice Board), then drains the Layer-2 worker over
    them: PDF download → extraction → publish gate. Published notifications
    carry official links (source_url/official_pdf_url = the government's own
    PDF/notice URL). Requires login and is globally throttled, because one
    call costs scrape + LLM work for everybody.
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

    from app.services import layer1_poller, layer2_worker

    try:
        for slug in layer2_worker.DEFAULT_SOURCES:
            await layer1_poller.run_once(only_slug=slug, ignore_schedule=True)
        stats = await layer2_worker.process_new_links(
            layer2_worker.DEFAULT_SOURCES, max_docs=5
        )
    except Exception:
        # A failed pass must not lock out retries for the whole cooldown.
        _last_sync_started_at = None
        # Do not reflect scraper/LLM exception text back to clients.
        logger.exception("Live job sync failed")
        raise HTTPException(
            status_code=502,
            detail="Live job sync failed. Please try again later.",
        )

    added_count = stats.auto
    skipped_count = (
        stats.review + stats.ignored + stats.failed + stats.skipped_attempts
    )

    total_active = (
        await db.execute(
            select(func.count())
            .select_from(ExamNotification)
            .where(ExamNotification.is_active.is_(True))
        )
    ).scalar_one()

    return {
        "status": "success",
        "new_jobs_discovered": added_count,
        "skipped_jobs": skipped_count,
        "total_active_jobs": total_active,
    }
