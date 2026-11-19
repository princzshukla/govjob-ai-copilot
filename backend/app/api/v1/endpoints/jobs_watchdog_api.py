# app/api/v1/endpoints/jobs_watchdog_api.py
"""Admin access to the Jobs Watchdog's reports and one-shot runs."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_admin
from app.core.database import get_db
from app.services import jobs_report
from app.services.jobs_watchdog import run_jobs_watchdog_pass
from scripts.listing_census import collect_census

router = APIRouter(prefix="/admin/jobs-watchdog", tags=["Admin: Jobs Watchdog"])


@router.get("/listing-census")
async def get_listing_census(admin=Depends(require_admin)):
    """Exact, live listing counts from both sarkariresult.com.cm pages."""
    return await collect_census()


@router.get("/report")
async def get_jobs_watchdog_report(db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    report = await jobs_report.latest_report(db)
    return {"report": report}


@router.post("/run")
async def run_jobs_watchdog(db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    """Run one watchdog pass on demand (same lock as the scheduled worker)."""
    result = await run_jobs_watchdog_pass()
    if result.get("status") == "ok" or result.get("skipped"):
        return result
    return result
