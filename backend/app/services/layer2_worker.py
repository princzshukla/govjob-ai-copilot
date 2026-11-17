# app/services/layer2_worker.py
"""Layer 2 worker: drain ``raw_discovered_links`` end to end, unattended.

Per link (Tier-1 sources by default: ``upsc-whats-new`` and
``ssc-notice-board``):

1. Download the PDF (httpx, magic-byte check, 25 MB cap).
2. Extract with ``notification_extractor`` (content-hash cache honored).
3. Gate: the row lands in ``extraction_results`` as ``auto`` or ``review``.
4. ``auto`` rows are promoted into ``exam_notifications`` (provenance kept);
   ``review`` rows wait in the review queue for a human.

Safety rails:

* **Daily token budget** — one row per UTC day in ``token_budget``; the env
  var ``WORKER_DAILY_TOKEN_BUDGET`` (default 40000, *estimated* tokens)
  stops the worker cleanly before it spends more. Estimates come from the
  same estimator the prompt uses, inflated 20% for output.
* **Attempt counter** — ``raw_discovered_links.process_attempts``; a link
  that fails 3 times is skipped with a loud log line.
* **No auto-publish without provenance** — the publisher's review gate
  applies unchanged; ``review`` rows are never published.

Run:
    python -m app.services.layer2_worker [--dry-run] [--source upsc-whats-new,ssc-notice-board] [--max-docs 50]
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

import httpx
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.pipeline import (
    ExtractionResult as ExtractionResultRow,
    RawDiscoveredLink,
    ScrapeSource,
    TokenBudget,
)
from app.services import admit_extractor
from app.services.exam_publisher import publish_auto_extractions
from app.services import notification_extractor as nx

logger = logging.getLogger(__name__)

MAX_PDF_BYTES = 25 * 1024 * 1024
MAX_ATTEMPTS = 3
DEFAULT_DAILY_BUDGET = 40000
DEFAULT_SOURCES = ("upsc-whats-new", "ssc-notice-board")
HTTP_HEADERS = {"User-Agent": "govjob-copilot/0.1 (notification ingestion; contact admin)"}
PDF_MAGIC = b"%PDF-"

_BUDGET_ENV = "WORKER_DAILY_TOKEN_BUDGET"

_ADMIT_RE = re.compile(
    r"\b(admit(?:\s|-)?card|admission certificate|exam city|hall.?ticket|participation certificate|call letter)\b",
    re.IGNORECASE,
)


def detect_notice_kind(link: RawDiscoveredLink, source: ScrapeSource | None) -> str:
    """Classify a discovered link as an admit card vs a job notification.

    The source can force the classification via ``config.notice_kind``;
    otherwise the headline/URL is matched for admit-card vocabulary (the SSC
    JSON API and UPSC What's New carry such headlines verbatim).
    """
    if source is not None:
        config = source.config if isinstance(source.config, dict) else {}
        if str(config.get("notice_kind") or "").strip().lower() == "admit_card":
            return "admit_card"
    haystack = f"{link.title or ''} {link.url or ''}"
    return "admit_card" if _ADMIT_RE.search(haystack) else "job"


async def _process_admit_link(
    db,
    link: RawDiscoveredLink,
    stats: WorkerStats,
    budget_left: float,
    pdf: bytes,
    *,
    dry_run: bool = False,
) -> str:
    """Admit-card branch: minimal extraction, same trust rails, own publish gate."""
    text, page_count, chars_per_page = nx.extract_text_stats(pdf)
    scanned = chars_per_page < nx.MIN_CHARS_PER_PAGE
    usage = 0.0 if scanned else _estimate_doc_tokens(len(text))

    if dry_run:
        stats.downloaded += 1
        stats.est_tokens_spent += usage
        stats.links.append(f"dry-run: {link.url} (~{usage:.0f} est tokens, admit card)")
        return "ok"

    if usage > budget_left:
        stats.budget_stopped = True
        logger.info("daily token budget reached (%.0f left, need ~%.0f) — stopping", budget_left, usage)
        return "budget"

    result = await admit_extractor.extract_admit_card(pdf, headline=link.title)
    stats.downloaded += 1
    stats.est_tokens_spent += usage
    if result.is_scanned or scanned:
        stats.scanned += 1
    status = "auto" if not result.needs_manual_review and not result.is_scanned else "review"

    await _budget_add(db, datetime.now(timezone.utc).date(), usage)
    iso = lambda d: d.isoformat() if d else None
    extracted = {
        "kind": "admit_card",
        "exam_name": result.exam_name,
        "exam_date": iso(result.exam_date),
        "notification_date": iso(result.notification_date),
    }
    db.add(
        ExtractionResultRow(
            raw_link_id=link.id,
            status=status,
            provider=result.provider,
            extracted=extracted,
            field_confidence=result.field_confidence or {},
            evidence=result.evidence or {},
            missing_fields=[f for f in ("exam_name",) if not result.exam_name],
            review_note="; ".join(result.review_reasons or []) or None,
        )
    )
    link.status = "processed"
    link.process_attempts += 1

    if status == "auto":
        stats.auto += 1
    else:
        stats.review += 1
    stats.links.append(f"{status} (admit): {link.url}")
    return status


@dataclass
class WorkerStats:
    downloaded: int = 0
    scanned: int = 0
    auto: int = 0
    review: int = 0
    ignored: int = 0
    failed: int = 0
    skipped_attempts: int = 0
    budget_stopped: bool = False
    est_tokens_spent: float = 0.0
    links: list[str] = field(default_factory=list)


def daily_budget() -> int:
    raw = os.environ.get(_BUDGET_ENV, "").strip()
    try:
        return int(raw) if raw else DEFAULT_DAILY_BUDGET
    except ValueError:
        logger.warning("ignoring unparseable %s=%r; using %d", _BUDGET_ENV, raw, DEFAULT_DAILY_BUDGET)
        return DEFAULT_DAILY_BUDGET


async def _budget_used(db, day: date) -> float:
    row = (await db.execute(select(TokenBudget).where(TokenBudget.day == day))).scalar_one_or_none()
    return float(row.tokens_used) if row else 0.0


async def _budget_add(db, day: date, tokens: float) -> None:
    row = (await db.execute(select(TokenBudget).where(TokenBudget.day == day))).scalar_one_or_none()
    if row is None:
        db.add(TokenBudget(day=day, tokens_used=int(tokens)))
    else:
        row.tokens_used = int(row.tokens_used + tokens)


def _estimate_doc_tokens(text_chars: float) -> float:
    """Rough, conservative estimate of one extraction call's total cost."""
    est = min(text_chars / 4.0, nx.TOKEN_BUDGET) + 400  # input (bounded) + envelope/system
    return est * 1.2 + 800  # output tokens + 20% safety margin


async def _fetch_pdf(url: str) -> bytes | None:
    async with httpx.AsyncClient(timeout=30.0, headers=HTTP_HEADERS, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        content = resp.content
    if len(content) > MAX_PDF_BYTES:
        logger.warning("skipping oversize document (%d bytes): %s", len(content), url)
        return None
    if not content.startswith(PDF_MAGIC):
        logger.info("not a PDF (magic bytes missing): %s", url)
        return None
    return content


async def process_link(
    db,
    link: RawDiscoveredLink,
    stats: WorkerStats,
    source_map: dict[int, ScrapeSource],
    budget_left: float,
    *,
    dry_run: bool = False,
) -> str:
    """Returns "auto" | "review" | "ignored" | "failed" | "skipped" | "budget"."""
    if link.process_attempts >= MAX_ATTEMPTS:
        stats.skipped_attempts += 1
        logger.warning("skipping %s — %d failed attempts", link.url, link.process_attempts)
        return "skipped"

    try:
        pdf = await _fetch_pdf(link.url)
    except Exception as exc:
        logger.warning("download failed for %s: %s", link.url, exc)
        link.process_attempts += 1
        stats.failed += 1
        return "failed"

    if pdf is None:
        if not dry_run:
            link.status = "ignored"
        stats.ignored += 1
        return "ignored"

    source = source_map.get(link.source_id)
    if detect_notice_kind(link, source) == "admit_card":
        return await _process_admit_link(db, link, stats, budget_left, pdf, dry_run=dry_run)

    text, page_count, chars_per_page = nx.extract_text_stats(pdf)
    if chars_per_page < nx.MIN_CHARS_PER_PAGE:
        logger.info("scanned/image PDF skipped from LLM entirely: %s", link.url)
        if dry_run:
            stats.scanned += 1
            stats.downloaded += 1
            stats.links.append(f"dry-run: {link.url} (scanned — would be review)")
            return "review"
        result = await nx.extract_notification(pdf, use_cache=True)
        usage = 0.0
    else:
        usage = _estimate_doc_tokens(len(text))
        if dry_run:
            stats.downloaded += 1
            stats.est_tokens_spent += usage
            stats.links.append(f"dry-run: {link.url} (~{usage:.0f} est tokens — not sent to LLM)")
            return "ok"
        if usage > budget_left:
            stats.budget_stopped = True
            logger.info("daily token budget reached (%.0f left, need ~%.0f) — stopping", budget_left, usage)
            return "budget"
        result = await nx.extract_notification(pdf, use_cache=True)

    stats.downloaded += 1
    stats.est_tokens_spent += usage

    if result.is_scanned:
        stats.scanned += 1
    status = "auto" if not result.needs_manual_review and not result.is_scanned else "review"

    if not dry_run:
        await _budget_add(db, datetime.now(timezone.utc).date(), usage)
        extracted = result.model_dump(mode="json")
        db.add(
            ExtractionResultRow(
                raw_link_id=link.id,
                status=status,
                provider=result.provider,
                extracted=extracted,
                field_confidence=result.field_confidence or {},
                evidence=result.evidence or {},
                missing_fields=[
                    f for f in nx.CRITICAL_FIELDS if getattr(result, f) in (None, "", {})
                ],
                review_note="; ".join(result.review_reasons or []) or None,
            )
        )
        link.status = "processed"
        link.process_attempts += 1

    if status == "auto":
        stats.auto += 1
    else:
        stats.review += 1
    stats.links.append(f"{'auto' if status == 'auto' else 'review'}: {link.url}")
    return status


async def process_new_links(
    source_slugs: tuple[str, ...] = DEFAULT_SOURCES,
    *,
    max_docs: int = 50,
    dry_run: bool = False,
) -> WorkerStats:
    stats = WorkerStats()
    async with AsyncSessionLocal() as db:
        sources = list(
            (
                await db.execute(
                    select(ScrapeSource).where(ScrapeSource.slug.in_(source_slugs), ScrapeSource.enabled.is_(True))
                )
            ).scalars().all()
        )
        source_map = {s.id: s for s in sources}
        day = datetime.now(timezone.utc).date()
        used = await _budget_used(db, day)
        limit = daily_budget()
        logger.info("token budget today: %.0f used / %d limit", used, limit)
        budget_left = limit - used
        for source in sources:
            if stats.budget_stopped:
                break
            rows = (
                await db.execute(
                    select(RawDiscoveredLink)
                    .where(RawDiscoveredLink.source_id == source.id, RawDiscoveredLink.status == "new")
                    .order_by(RawDiscoveredLink.first_seen_at)
                    .limit(max_docs)
                )
            ).scalars().all()
            for link in rows:
                if stats.budget_stopped:
                    break
                if stats.downloaded >= max_docs:
                    break
                outcome = await process_link(db, link, stats, source_map, budget_left, dry_run=dry_run)
                if outcome == "budget":
                    break
                budget_left = max(0.0, limit - used - stats.est_tokens_spent)
        if not dry_run:
            await db.commit()
        if not dry_run:
            report = await publish_auto_extractions(db)
            logger.info(
                "publish gate: %d published, %d held", len(report.published), len(report.held)
            )
            from app.services.admit_publisher import publish_auto_admit_cards

            admit_report = await publish_auto_admit_cards(db)
            logger.info(
                "admit-card publish gate: %d published, %d held",
                len(admit_report.published),
                len(admit_report.held),
            )

    logger.info(
        "worker done: downloaded=%d scanned=%d auto=%d review=%d ignored=%d failed=%d skipped_attempts=%d budget_stopped=%s est_tokens=%.0f",
        stats.downloaded, stats.scanned, stats.auto, stats.review, stats.ignored,
        stats.failed, stats.skipped_attempts, stats.budget_stopped, stats.est_tokens_spent,
    )
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Layer 2 worker: new links → extract → review/publish")
    parser.add_argument("--dry-run", action="store_true", help="fetch and estimate only; no DB writes, no LLM")
    parser.add_argument("--source", default=",".join(DEFAULT_SOURCES), help="comma-separated source slugs")
    parser.add_argument("--max-docs", type=int, default=50)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    slugs = tuple(s.strip() for s in args.source.split(",") if s.strip())
    stats = asyncio.run(process_new_links(slugs, max_docs=args.max_docs, dry_run=args.dry_run))
    if args.dry_run:
        print("dry-run: nothing written")
    print(
        f"downloaded={stats.downloaded} auto={stats.auto} review={stats.review} "
        f"ignored={stats.ignored} failed={stats.failed} budget_stopped={stats.budget_stopped} "
        f"est_tokens={stats.est_tokens_spent:.0f}"
    )


if __name__ == "__main__":
    main()
