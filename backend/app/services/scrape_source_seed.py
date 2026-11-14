"""Idempotently seed the Layer 1 poll registry (scrape_sources).

Usage:
    python -m app.services.scrape_source_seed              # upsert
    python -m app.services.scrape_source_seed --dry-run    # print only

Tier-1 intervals are set to 120s per the pipeline test protocol; raise them
for production via --tier1-interval (e.g. 600). Tier 3 stays slow because a
change there is rare and a changed-less poll costs one GET + one hash.

The local-test-notices source expects test_notices.html served on port 8001:
    python -m http.server 8001 --directory scripts/fixtures
"""
from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.pipeline import ScrapeSource

# link_pattern shared by the HTML sources: PDF attachments and notice-like paths.
_PDF_OR_NOTICE = r"\.pdf($|\?)|/(notice|notification|recruitment|advertisement|advt)|/media/file/"

SOURCES: list[dict] = [
    {
        "slug": "upsc-whats-new",
        "name": "UPSC — What's New",
        "url": "https://www.upsc.gov.in/whats-new",
        "tier": 1,
        "fetch_mode": "httpx",
        "css_selector": "div.view-what-new",
        "ignore_selector": None,  # scope already excludes the carousel; hash strips counters
        "link_pattern": r"\.pdf($|\?)|whats-new/|advt|notice",
        "interval_seconds": 120,
    },
    {
        "slug": "ssccr-announcements",
        "name": "SSC (Regional CR) — Announcements",
        "url": "https://ssccr.gov.in/announcements",
        "tier": 1,
        "fetch_mode": "httpx",
        "css_selector": '[data-slot="table-body"]',
        "ignore_selector": None,
        "link_pattern": r"/api/media/file/|\.pdf($|\?)",
        "interval_seconds": 120,
    },
    {
        # ssc.gov.in is a pure Angular SPA with no SSR content. Its notice
        # board is backed by an unauthenticated JSON endpoint, which is what
        # the Angular client itself calls; hitting it directly beats
        # rendering the page with Playwright.
        "slug": "ssc-notice-board",
        "name": "SSC — Notice Board (JSON API)",
        "url": "https://ssc.gov.in/api/general-website/portal/notice-boards",
        "tier": 1,
        "fetch_mode": "json_api",
        "link_pattern": None,
        "interval_seconds": 120,
        "config": {
            "params": {
                "page": 1,
                "limit": 10,
                "contentType": "notice-boards",
                "key": "createdAt",
                "order": "DESC",
                "isAttachment": "true",
                "language": "english",
                "attributes": "id,headline,examId,contentType,redirectUrl,startDate,endDate,language,createdAt",
            },
            "items_path": "data",
            "id_field": "id",
            "date_field": "createdAt",
            "title_field": "headline",
            "attachments_field": "attachments",
            # From fileService.openPDF(fileName, "NoticeBoards"):
            # ${apiUrlFileServer}/attachment/uploads/masterData/NoticeBoards/<fileName>
            "file_url_template": "https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/{fileName}",
        },
    },
    {
        # State portal with NIC hosting quirks (slow TLS, frequent timeouts).
        # css_selector intentionally unset until the 48h stability run shows
        # which elements flap; tighten then. Whole-page hashing is noisy for
        # pages with counters — expect false positives until scoped.
        "slug": "uppsc-home",
        "name": "UPPSC — Home / Notices",
        "url": "https://uppsc.up.nic.in/",
        "tier": 1,
        "fetch_mode": "httpx",
        "css_selector": None,
        "ignore_selector": None,
        "link_pattern": r"\.pdf($|\?)|notice|advt|recruit",
        "interval_seconds": 120,
    },
    {
        # Tier 3 — slow-moving PSU. Correct behaviour: unchanged page must
        # cost one GET + one hash and skip extraction entirely.
        # NB: NTPC (ntpc.co.in) is behind a Radware JS bot challenge — from a
        # plain HTTP client it serves a rotating-token shell, so it was
        # swapped for BHEL, which also rotates CSP nonces (stripped in the
        # normalizer). NTPC would need Playwright + challenge tolerance.
        "slug": "bhel-careers",
        "name": "BHEL — Careers",
        "url": "https://careers.bhel.in/index.jsp",
        "tier": 3,
        "fetch_mode": "httpx",
        "css_selector": None,
        "ignore_selector": None,
        "link_pattern": _PDF_OR_NOTICE,
        "interval_seconds": 3600,
    },
    {
        "slug": "local-test-notices",
        "name": "LOCAL — test_notices.html (Layer 1 test fixture)",
        "url": "http://127.0.0.1:8001/test_notices.html",
        "tier": 1,
        "fetch_mode": "httpx",
        "css_selector": "#notices",
        "ignore_selector": "#visitor-count",
        "link_pattern": None,
        "interval_seconds": 120,
    },
]


async def seed(dry_run: bool = False, tier1_interval: int | None = None) -> None:
    async with AsyncSessionLocal() as db:
        for spec in SOURCES:
            spec = dict(spec)
            if tier1_interval and spec.get("tier") == 1:
                spec["interval_seconds"] = tier1_interval
            existing = (
                await db.execute(select(ScrapeSource).where(ScrapeSource.slug == spec["slug"]))
            ).scalar_one_or_none()
            if existing is None:
                if dry_run:
                    print(f"would CREATE {spec['slug']}")
                    continue
                db.add(ScrapeSource(enabled=True, consecutive_failures=0, **spec))
                print(f"created {spec['slug']}")
            else:
                if dry_run:
                    print(f"would UPDATE {spec['slug']}")
                    continue
                for key, value in spec.items():
                    if key != "slug":
                        setattr(existing, key, value)
                print(f"updated {spec['slug']}")
        if not dry_run:
            await db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed scrape_sources (idempotent upsert)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--tier1-interval",
        type=int,
        default=None,
        help="override the Tier-1 poll interval in seconds (e.g. 600 for production)",
    )
    args = parser.parse_args()
    asyncio.run(seed(dry_run=args.dry_run, tier1_interval=args.tier1_interval))


if __name__ == "__main__":
    main()
