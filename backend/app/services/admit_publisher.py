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
