"""Admit-card publish gate — Layer 2 → admit_cards.

Mirrors exam_publisher's trust semantics, minus everything an admit card does
not have: no eligibility, no application window. Promotes
``extraction_results`` rows with ``extracted->>'kind'='admit_card'`` that
passed the extraction gate (``status='auto'``) into ``admit_cards``.

* Only once per row (``admit_card_id`` back-reference is idempotent).
* Nothing is invented: the official download link is always the discovered
  link URL; exam name falls back to the headline; missing/untrusted rows are
  **held** — flipped back to ``review`` with a machine-readable note.
* ``is_scanned`` rows never reach here — they are ``review`` at extraction.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.admit_card import AdmitCardNotification
from app.models.pipeline import ExtractionResult, RawDiscoveredLink, ScrapeSource

logger = logging.getLogger(__name__)


@dataclass
class PublishOutcome:
    extraction_id: int
    action: str  # "published" | "held"
    detail: str
    admit_card_id: str | None = None


@dataclass
class PublishReport:
    published: list[PublishOutcome] = field(default_factory=list)
    held: list[PublishOutcome] = field(default_factory=list)

    @property
    def total_considered(self) -> int:
        return len(self.published) + len(self.held)


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _build_id(extraction_id: int) -> str:
    return f"admit-ext-{extraction_id}"


def build_admit_card(
    extraction: ExtractionResult,
    link: RawDiscoveredLink,
    source: ScrapeSource,
) -> tuple[AdmitCardNotification | None, list[str]]:
    """Pure mapping extraction_row + link + source -> AdmitCardNotification."""
    data: dict[str, Any] = extraction.extracted or {}
    problems: list[str] = []

    config = source.config if isinstance(source.config, dict) else {}
    organizing_body = str(config.get("organizing_body") or source.name)[:100]

    exam_name = (str(data.get("exam_name") or "").strip() or None)
    headline = (link.title or "").strip() or None
    title = (headline or exam_name or "")[:255]
    if not title:
        problems.append("exam_name missing and link has no headline")

    admit_url = link.url  # always the board's own official link — never constructed
    if not admit_url or not admit_url.lower().startswith(("http://", "https://")):
        problems.append("link.url is not a valid http(s) URL")

    if problems:
        return None, problems

    exam_date = _parse_date(data.get("exam_date"))
    notification_date = (
        link.published_at.date()
        if link.published_at
        else _parse_date(data.get("notification_date"))
    )

    card = AdmitCardNotification(
        id=_build_id(extraction.id),
        notice_subtype=str(data.get("subtype") or "admit_card")[:20],
        title=title,
        organizing_body=organizing_body,
        exam_name=(exam_name or title)[:255],
        notification_date=notification_date,
        exam_date=exam_date,
        admit_url=admit_url,
        source_url=link.url,
        last_checked_at=date.today(),
        is_active=True,
    )
    return card, []


def _hold(extraction: ExtractionResult, reasons: list[str], dry_run: bool) -> PublishOutcome:
    note = "admit-card publish gate: " + "; ".join(reasons)
    logger.warning("extraction %s held from admit_cards — %s", extraction.id, note)
    if not dry_run:
        extraction.status = "review"
        previous = (extraction.review_note or "").strip()
        extraction.review_note = f"{previous} | {note}" if previous else note
    return PublishOutcome(extraction_id=extraction.id, action="held", detail=note)


async def publish_auto_admit_cards(
    db: AsyncSession, *, dry_run: bool = False
) -> PublishReport:
    """Promote every unpromoted status='admit-card auto' extraction."""
    rows = (
        await db.execute(
            select(ExtractionResult, RawDiscoveredLink, ScrapeSource)
            .join(RawDiscoveredLink, ExtractionResult.raw_link_id == RawDiscoveredLink.id)
            .join(ScrapeSource, RawDiscoveredLink.source_id == ScrapeSource.id)
            .where(
                ExtractionResult.status == "auto",
                ExtractionResult.admit_card_id.is_(None),
                # only rows the admit-card extractor produced
                ExtractionResult.extracted["kind"].astext == "admit_card",
            )
            .order_by(ExtractionResult.id)
        )
    ).all()

    report = PublishReport()
    for extraction, link, source in rows:
        # Dedup: the official notice may already have a curated seed card
        # (or an earlier pipeline-published one) with the same admit_url.
        # Adopt it — refresh last_checked_at — instead of duplicating.
        existing = (
            await db.execute(
                select(AdmitCardNotification).where(
                    AdmitCardNotification.admit_url == link.url
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            if not dry_run:
                from app.core.timeutils import today_ist

                data = extraction.extracted or {}
                existing.last_checked_at = today_ist()
                # Adopt = refresh, not degrade: fill dates the board publishes
                # only on the notice itself, when our seed has none. Never
                # overwrite a date we already trust.
                ext_exam = _parse_date(data.get("exam_date"))
                if ext_exam and not existing.exam_date:
                    existing.exam_date = ext_exam
                ext_notif = _parse_date(data.get("notification_date"))
                if ext_notif and not existing.notification_date:
                    existing.notification_date = ext_notif
                extraction.admit_card_id = existing.id
                link.status = "processed"
            detail = f"adopted existing admit card {existing.id} ({link.url[:70]})"
            if not dry_run:
                logger.info("admit-card publish gate: %s", detail)
            report.published.append(
                PublishOutcome(
                    extraction_id=extraction.id,
                    action="published",
                    detail=detail,
                    admit_card_id=existing.id,
                )
            )
            continue

        card, problems = build_admit_card(extraction, link, source)
        if card is None:
            report.held.append(_hold(extraction, problems, dry_run))
            continue
        if not dry_run:
            db.add(card)
            extraction.admit_card_id = card.id
            link.status = "processed"
        report.published.append(
            PublishOutcome(
                extraction_id=extraction.id,
                action="published",
                detail=f"{card.organizing_body} — {card.title[:80]}",
                admit_card_id=card.id,
            )
        )

    if not dry_run and report.total_considered:
        await db.commit()
    return report
