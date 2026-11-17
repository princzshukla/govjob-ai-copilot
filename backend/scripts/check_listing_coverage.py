"""Coverage watchdog CLI — run from the backend directory.

    python scripts/check_listing_coverage.py            # report vs live latest-jobs page
    python scripts/check_listing_coverage.py --json     # machine-readable
    python scripts/check_listing_coverage.py --alert    # Telegram admin alert if gaps
    python scripts/check_listing_coverage.py --fail-on-missing   # exit 1 when gaps (CI)
    python scripts/check_listing_coverage.py --html-file page.html  # offline parse

Discovery-only: lists live aggregator entries missing from the seed so a
human can add them from the official PDFs. Never writes to the database and
never publishes anything.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.coverage_watchdog import (  # noqa: E402
    ADMIT_CARD_MATCH_THRESHOLD,
    ADMIT_CARD_URL,
    DEFAULT_MATCH_THRESHOLD,
    LATEST_JOBS_URL,
    build_report,
    check_coverage,
    format_report,
    parse_admit_cards_page,
    parse_latest_jobs,
    seed_admit_titles,
    seed_titles,
    send_watchdog_alert,
)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default=LATEST_JOBS_URL, help="latest-jobs page to check")
    parser.add_argument("--html-file", type=Path, default=None, help="parse a saved page instead of fetching")
    parser.add_argument("--threshold", type=float, default=DEFAULT_MATCH_THRESHOLD, help="match score 0..1")
    parser.add_argument("--all", action="store_true", help="include stale/archived entries with no parseable future last date")
    parser.add_argument("--admit-cards", action="store_true", help="check admit-card coverage instead of latest jobs")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    parser.add_argument("--alert", action="store_true", help="send Telegram admin alert when gaps found")
    parser.add_argument("--fail-on-missing", action="store_true", help="exit 1 when gaps are found")
    args = parser.parse_args()

    kind = "admit_card" if args.admit_cards else "latest_jobs"
    default_url = ADMIT_CARD_URL if args.admit_cards else LATEST_JOBS_URL
    if args.html_file is not None:
        page_html = args.html_file.read_text(encoding="utf-8")
        if kind == "admit_card":
            entries = parse_admit_cards_page(page_html)
            report = build_report(
                entries,
                seed_admit_titles(),
                threshold=ADMIT_CARD_MATCH_THRESHOLD,
                source_url=str(args.html_file),
                kind=kind,
            )
        else:
            entries = parse_latest_jobs(page_html)
            report = build_report(
                entries,
                seed_titles(),
                threshold=args.threshold,
                source_url=str(args.html_file),
                actionable_only=not args.all,
                kind=kind,
            )
    else:
        report = asyncio.run(check_coverage(args.url if args.url != LATEST_JOBS_URL else default_url, threshold=args.threshold, actionable_only=not args.all, kind=kind))

    if args.json:
        print(json.dumps({
            "kind": report.kind,
            "source_url": report.source_url,
            "live_entries": len(report.entries),
            "seed_rows": report.seed_count,
            "matched": len(report.matched),
            "coverage_pct": report.coverage_pct,
            "missing": [asdict(e) for e in report.missing],
        }, indent=2, ensure_ascii=False))
    else:
        print(format_report(report))

    if args.alert:
        asyncio.run(send_watchdog_alert(report))

    if args.fail_on_missing and report.missing:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
