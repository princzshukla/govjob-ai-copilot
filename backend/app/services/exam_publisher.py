# app/services/exam_publisher.py
"""Layer 2 → Layer 3 bridge.

Promotes ``extraction_results`` rows that passed the extraction trust gate
(``status = 'auto'``) into ``exam_notifications`` so the matcher and the
Telegram digests can see them — with official-PDF provenance on every row.

Trust semantics (deliberately strict):

* Only ``status = 'auto'`` rows are considered, and only once (rows with an
  ``exam_notification_id`` are skipped — re-running is idempotent).
* Nothing is invented. If a required ``exam_notifications`` value cannot be
  filled from the extraction or the discovered link, the row is **held**:
  ``status`` flips back to ``review`` with a machine-readable ``review_note``
  explaining exactly why, and no ``exam_notifications`` row is created.
* ``is_scanned`` rows never reach here — they are ``review`` at extraction time.
* ``age_relaxations`` detected by the extractor are NOT copied into
  ``exam_notifications`` (the column does not exist yet; the matcher applies
  statutory relaxations). They remain available in
  ``extraction_results.extracted`` for audit.

Usage:
    python -m app.services.exam_publisher [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.exam import ExamNotification
from app.models.pipeline import ExtractionResult, RawDiscoveredLink, ScrapeSource
from app.services.matcher import degrees_and_streams_from_text

logger = logging.getLogger(__name__)


@dataclass
class PublishOutcome:
    extraction_id: int
    action: str  # "published" | "held" | "skipped"
    detail: str
    exam_id: str | None = None


@dataclass
class PublishReport:
    published: list[PublishOutcome] = field(default_factory=list)
    held: list[PublishOutcome] = field(default_factory=list)

    @property
    def total_considered(self) -> int:
        return len(self.published) + len(self.held)


def _parse_date(value: Any) -> date | None:
    """Accept ISO date strings (JSONB storage) or date/datetime objects."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _parse_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _valid_apply_url(value: Any) -> str | None:
    """Accept only http(s) URLs as ``apply_url``; anything else is dropped."""
    import re as _re

    if not isinstance(value, str):
        return None
    url = value.strip()
    if not url or len(url) > 500 or any(ch.isspace() for ch in url):
        return None
    if not _re.match(r"^https?://[A-Za-z0-9.\-]+(/|$)", url, _re.IGNORECASE):
        return None
    return url


def _hold(extraction: ExtractionResult, reasons: list[str], dry_run: bool) -> PublishOutcome:
    note = "publish gate: " + "; ".join(reasons)
    logger.warning("extraction %s held from publish — %s", extraction.id, note)
    if not dry_run:
        extraction.status = "review"
        previous = (extraction.review_note or "").strip()
        extraction.review_note = f"{previous} | {note}" if previous else note
    return PublishOutcome(extraction_id=extraction.id, action="held", detail=note)


def _build_exam_id(extraction_id: int) -> str:
    return f"ext-{extraction_id}"


def build_exam_notification(
    extraction: ExtractionResult,
    link: RawDiscoveredLink,
    source: ScrapeSource,
) -> tuple[ExamNotification | None, list[str]]:
    """Pure mapping extraction_row + link + source -> ExamNotification.

    Returns (exam, problems). ``exam`` is None when ``problems`` is non-empty;
    every problem is evidence for the hold note, never a guessed value.
    """
    data: dict[str, Any] = extraction.extracted or {}
    problems: list[str] = []

    min_age = _parse_int(data.get("min_age"))
    if min_age is None:
        problems.append("min_age missing (notification does not state one, or extraction could not read it)")

    max_age = _parse_int(data.get("age_max_general"))
    if max_age is None:
        problems.append("age_max_general missing")

    cutoff = _parse_date(data.get("age_cutoff_date"))
    if cutoff is None:
        problems.append("age_cutoff_date missing/unparseable")

    deadline = _parse_date(data.get("application_last_date"))
    if deadline is None:
        problems.append("application_last_date missing/unparseable")

    qualification = str(data.get("required_qualification") or "").strip()
    degrees, streams = degrees_and_streams_from_text(qualification)
    if not degrees:
        problems.append(f"required_qualification maps to no known degree: {qualification[:120]!r}")

    if problems:
        return None, problems

    config = source.config if isinstance(source.config, dict) else {}
    organizing_body = str(config.get("organizing_body") or source.name)[:100]
    title = (link.title or f"{organizing_body} — notification")[:255]
    exam_id = _build_exam_id(extraction.id)
    apply_url = _valid_apply_url(data.get("apply_url"))

    exam = ExamNotification(
        id=exam_id,
        title=title,
        organizing_body=organizing_body,
        post_type="General",
        notification_date=link.published_at.date() if link.published_at else None,
        application_deadline=deadline,
        exam_date=None,
        official_pdf_url=link.url,
        apply_url=apply_url,
        min_age=min_age,
        max_age_general=max_age,
        age_cutoff_date=cutoff,
        allowed_degrees=degrees,
        allowed_streams=streams or None,
        min_percentage=0.0,  # not extracted; 0 = no percentage floor
        topics=[],
        state_restriction=None,
        allows_final_year=None,  # unstated -> matcher asks for manual check
        max_attempts=None,
        source_url=link.url,
        last_checked_at=date.today(),
        is_active=True,
    )
    return exam, []


async def publish_auto_extractions(
    db: AsyncSession, *, dry_run: bool = False
) -> PublishReport:
    """Promote every unpromoted status='auto' extraction. One commit at the end."""
    rows = (
        await db.execute(
            select(ExtractionResult, RawDiscoveredLink, ScrapeSource)
            .join(RawDiscoveredLink, ExtractionResult.raw_link_id == RawDiscoveredLink.id)
            .join(ScrapeSource, RawDiscoveredLink.source_id == ScrapeSource.id)
            .where(
                ExtractionResult.status == "auto",
                ExtractionResult.exam_notification_id.is_(None),
            )
            .order_by(ExtractionResult.id)
        )
    ).all()

    report = PublishReport()
    for extraction, link, source in rows:
        exam, problems = build_exam_notification(extraction, link, source)
        if exam is None:
            outcome = _hold(extraction, problems, dry_run)
            report.held.append(outcome)
            continue
        if not dry_run:
            db.add(exam)
            extraction.exam_notification_id = exam.id
            link.status = "processed"
        report.published.append(
            PublishOutcome(
                extraction_id=extraction.id,
                action="published",
                detail=f"{exam.organizing_body} — {exam.title[:80]} (deadline {exam.application_deadline})",
                exam_id=exam.id,
            )
        )

    if not dry_run and report.total_considered:
        await db.commit()
    if not dry_run and report.published:
        # Operator digest for newly-promoted exams. Inert unless configured
        # (MAIL_PROVIDER/MAIL_DIGEST_TO). Never breaks the publish path.
        try:
            from app.services.mailer import send_exam_digest

            ids = [p.exam_id for p in report.published]
            promoted = (
                (await db.execute(select(ExamNotification).where(ExamNotification.id.in_(ids))))
                .scalars()
                .all()
            )
            send_exam_digest(
                [
                    {
                        "title": e.title,
                        "organizing_body": e.organizing_body,
                        "application_deadline": e.application_deadline.isoformat() if e.application_deadline else "",
                        "official_pdf_url": e.official_pdf_url or "",
                        "apply_url": e.apply_url or "",
                    }
                    for e in promoted
                ]
            )
        except Exception:
            logger.exception("publish digest email failed — digest skipped")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote status='auto' extractions into exam_notifications")
    parser.add_argument("--dry-run", action="store_true", help="print what would happen; change nothing")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    async def run() -> int:
        async with AsyncSessionLocal() as db:
            report = await publish_auto_extractions(db, dry_run=args.dry_run)
        print(f"considered: {report.total_considered}  published: {len(report.published)}  held: {len(report.held)}")
        for outcome in report.published:
            print(f"  [published] extraction {outcome.extraction_id} -> {outcome.exam_id}  {outcome.detail}")
        for outcome in report.held:
            print(f"  [held]      extraction {outcome.extraction_id}  {outcome.detail}")
        if args.dry_run:
            print("dry-run: no changes written")
        return 0

    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
