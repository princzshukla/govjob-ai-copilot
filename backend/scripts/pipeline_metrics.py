"""Pipeline metrics & duplicate report — run from the backend directory.

    python scripts/pipeline_metrics.py             # freshness / health report
    python scripts/pipeline_metrics.py --duplicates # cross-source dedup report

Freshness metric: for links whose source exposes a publish timestamp
(SSC notices carry ``createdAt``; most HTML portals do not),
``time-to-listing = first_seen_at - published_at``.

Health: per source, poll counts, success rate, zero-link streak and failure
streak (errors in the last 20 runs), current backoff state. HTML sources with
no ``published_at`` show "n/a" for lag — that is a data limitation, not a
bug.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select, func, text, case

from app.core.database import AsyncSessionLocal
from app.models.pipeline import RawDiscoveredLink, ScrapeLog, ScrapeSource


async def duplicates_report() -> None:
    async with AsyncSessionLocal() as db:
        rows = (
            await db.execute(
                select(
                    RawDiscoveredLink.dedup_key,
                    func.count(func.distinct(RawDiscoveredLink.source_id)).label("sources"),
                    func.count().label("links"),
                    func.array_agg(func.distinct(ScrapeSource.slug)).label("slugs"),
                )
                .join(ScrapeSource, ScrapeSource.id == RawDiscoveredLink.source_id)
                .where(RawDiscoveredLink.dedup_key.is_not(None))
                .group_by(RawDiscoveredLink.dedup_key)
                .having(func.count(func.distinct(RawDiscoveredLink.source_id)) > 1)
                .order_by(func.count(func.distinct(RawDiscoveredLink.source_id)).desc())
            )
        ).all()
        if not rows:
            print("No cross-source duplicates found (needs ≥2 sources reporting the same ad number).")
            return
        print(f"{'dedup_key':<12} {'sources':>7} {'links':>5}  sources")
        for dedup_key, sources, links, slugs in rows:
            print(f"{dedup_key:<12} {sources:>7} {links:>5}  {', '.join(sorted(slugs))}")


async def metrics_report() -> None:
    async with AsyncSessionLocal() as db:
        sources = list((await db.execute(select(ScrapeSource).order_by(ScrapeSource.tier, ScrapeSource.id))).scalars().all())
        lag_rows = (
            await db.execute(
                select(
                    ScrapeSource.slug,
                    func.avg(func.extract("epoch", RawDiscoveredLink.first_seen_at - RawDiscoveredLink.published_at)).label("avg_lag_s"),
                    func.min(func.extract("epoch", RawDiscoveredLink.first_seen_at - RawDiscoveredLink.published_at)).label("min_lag_s"),
                    func.max(func.extract("epoch", RawDiscoveredLink.first_seen_at - RawDiscoveredLink.published_at)).label("max_lag_s"),
                    func.count().label("timed_links"),
                )
                .join(RawDiscoveredLink, RawDiscoveredLink.source_id == ScrapeSource.id)
                .where(RawDiscoveredLink.published_at.is_not(None))
                .group_by(ScrapeSource.slug)
            )
        ).all()
        lag_by_slug = {row.slug: row for row in lag_rows}

        print(f"{'source':<22} {'tier':>4} {'polls':>6} {'ok%':>5} {'lag(avg)':>9} {'lag(max)':>9} {'zero-streak':>11} {'err-streak':>10} {'backoff'}")
        for source in sources:
            stats = (
                await db.execute(
                    select(
                        func.count().label("polls"),
                        func.sum(case((ScrapeLog.ok.is_(True), 1), else_=0)).label("ok_polls"),
                    ).where(ScrapeLog.source_id == source.id)
                )
            ).one()
            recent_errors = (
                await db.execute(
                    select(func.count())
                    .select_from(ScrapeLog)
                    .where(
                        ScrapeLog.source_id == source.id,
                        ScrapeLog.ok.is_(False),
                        ScrapeLog.started_at >= func.now() - text("interval '7 days'"),
                    )
                )
            ).scalar_one()
            lag = lag_by_slug.get(source.slug)
            lag_avg = f"{lag.avg_lag_s/3600:.1f}h" if lag and lag.avg_lag_s is not None else "n/a"
            lag_max = f"{lag.max_lag_s/3600:.1f}h" if lag and lag.max_lag_s is not None else "n/a"
            ok_pct = (stats.ok_polls or 0) * 100 // stats.polls if stats.polls else 0
            backoff = "yes" if source.backoff_until else "-"
            print(
                f"{source.slug:<22} {source.tier:>4} {stats.polls:>6} {ok_pct:>4}% "
                f"{lag_avg:>9} {lag_max:>9} {source.consecutive_zero_runs:>11} {recent_errors:>10} {backoff}"
            )


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    parser = argparse.ArgumentParser()
    parser.add_argument("--duplicates", action="store_true", help="report cross-source duplicates by dedup_key")
    args = parser.parse_args()
    if args.duplicates:
        asyncio.run(duplicates_report())
    else:
        asyncio.run(metrics_report())


if __name__ == "__main__":
    main()
