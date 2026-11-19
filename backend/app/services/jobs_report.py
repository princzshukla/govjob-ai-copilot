"""Structured Jobs Watchdog reporting.

Coverage is reported alongside its caveats. A feed parse that finds no
entries, or a perfect-looking match count with ambiguous/duplicate candidates,
is explicitly flagged as not honest — never shown as a clean 100%.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select

from app.core.timeutils import today_ist
from app.models.exam import ExamNotification
from app.models.exam_changes import JobsWatchdogReport
from app.models.discovery import NotificationDiscovery
from app.services import jobs_watchdog as jw

logger = logging.getLogger(__name__)

APPROACHING_DAYS = 30
_FINAL_STATUSES = ("approved", "rejected", "duplicate")


async def build_jobs_watchdog_report(db, coverage_report, discovery_stats: dict,
                                     deadline_stats: dict,
                                     census: dict | None = None) -> dict:
    today = today_ist()
    awaiting = (await db.execute(
        select(func.count(NotificationDiscovery.id)).where(
            NotificationDiscovery.notification_kind == "job",
            NotificationDiscovery.discovery_status.notin_(_FINAL_STATUSES),
        )
    )).scalar_one()
    new_since = datetime.combine(today, time.min, tzinfo=timezone.utc)
    newly = (await db.execute(
        select(func.count(NotificationDiscovery.id)).where(
            NotificationDiscovery.notification_kind == "job",
            NotificationDiscovery.classification == jw.CLASS_NEW,
            NotificationDiscovery.created_at >= new_since,
        )
    )).scalar_one()
    approaching = (await db.execute(
        select(func.count(ExamNotification.id)).where(
            ExamNotification.is_active.is_(True),
            ExamNotification.application_deadline >= today,
            ExamNotification.application_deadline <= today + timedelta(days=APPROACHING_DAYS),
        )
    )).scalar_one()

    ambiguous = len(coverage_report.ambiguous)
    duplicates = sum(len(v) for v in coverage_report.duplicate_matches.values())
    unmatched = len(coverage_report.missing)
    honest = not (unmatched or ambiguous or duplicates)
    notes: list[str] = []
    coverage_pct = coverage_report.coverage_pct
    if not coverage_report.entries:
        coverage_pct = None
        honest = False
        notes.append("aggregator feed parsed zero entries — markup may have changed; coverage is unknown")
    if unmatched or ambiguous or duplicates:
        notes.append(
            f"{unmatched} unmatched, {ambiguous} ambiguous and {duplicates} duplicate "
            "candidates are excluded from the coverage percentage"
        )
    if census:
        jobs_count = census.get("jobs", {}).get("raw_listings")
        if jobs_count is not None and jobs_count != len(coverage_report.entries):
            honest = False
            notes.append(
                f"listing census rendered {jobs_count} jobs but the parser read "
                f"{len(coverage_report.entries)} — counts disagree"
            )
        if not census.get("markup_ok"):
            honest = False
            notes.append("listing markup drift detected: " + "; ".join(census.get("drift", [])))
    data = {
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_url": coverage_report.source_url,
        "total_live": len(coverage_report.entries),
        "total_seeds": coverage_report.seed_count,
        "distinct_matched_seeds": len(coverage_report.distinct_matched_seeds),
        "coverage_pct": coverage_pct,
        "unmatched": unmatched,
        "duplicate_candidates": duplicates,
        "ambiguous": ambiguous,
        "newly_discovered": newly,
        "official_pdfs_verified": discovery_stats.get("pdf_verified", 0),
        "awaiting_review": awaiting,
        "deadlines_approaching": approaching,
        "honest": honest,
        "coverage_note": " ".join(notes) or "counts are one-to-one; no unverified job is published",
        "discovery_stats": discovery_stats,
        "deadline_stats": deadline_stats,
        "listing_census": census,
        "deadlines_approaching_days": APPROACHING_DAYS,
    }
    db.add(JobsWatchdogReport(
        total_live=data["total_live"], total_seeds=data["total_seeds"],
        distinct_matched_seeds=data["distinct_matched_seeds"], unmatched=unmatched,
        duplicate_candidates=duplicates, ambiguous=ambiguous, newly_discovered=newly,
        official_pdfs_verified=data["official_pdfs_verified"], awaiting_review=awaiting,
        deadlines_approaching=approaching, coverage_pct=coverage_pct,
        honest=honest, payload=data,
    ))
    await db.commit()
    return data


def format_jobs_report(data: dict) -> str:
    pct = "unknown" if data.get("coverage_pct") is None else f"{data['coverage_pct']}%"
    census = data.get("listing_census") or {}
    jobs_c = census.get("jobs") or {}
    admit_c = census.get("admit_cards") or {}
    census_line = (
        f"site census (exact): jobs {jobs_c.get('raw_listings', '?')} listed / "
        f"{jobs_c.get('effective_listings', '?')} relevant | admit cards "
        f"{admit_c.get('raw_listings', '?')} listed / {admit_c.get('effective_listings', '?')} relevant"
    ) if census else "site census (exact): not collected"
    lines = [
        "Jobs Watchdog report — strict 0.72 one-to-one matching",
        census_line,
        f"live job notifications: {data.get('total_live', 0)} | seed records: {data.get('total_seeds', 0)}",
        f"distinct seeds matched: {data.get('distinct_matched_seeds', 0)} | coverage (matched/live): {pct}",
        f"unmatched: {data.get('unmatched', 0)} | duplicate candidates: "
        f"{data.get('duplicate_candidates', 0)} | ambiguous: {data.get('ambiguous', 0)}",
        f"newly discovered: {data.get('newly_discovered', 0)} | official PDFs verified: "
        f"{data.get('official_pdfs_verified', 0)} | awaiting review: {data.get('awaiting_review', 0)}",
        f"deadlines approaching ({data.get('deadlines_approaching_days', 30)}d): "
        f"{data.get('deadlines_approaching', 0)}",
        f"honest: {data.get('honest')} — {data.get('coverage_note', '')}",
        "Nothing is published without official evidence and human approval.",
    ]
    return "\n".join(lines)


async def latest_report(db) -> dict | None:
    row = (await db.execute(
        select(JobsWatchdogReport).order_by(JobsWatchdogReport.id.desc()).limit(1)
    )).scalar_one_or_none()
    return row.payload if row else None
