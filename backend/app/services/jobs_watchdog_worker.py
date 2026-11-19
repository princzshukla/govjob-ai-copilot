"""One-shot Jobs Watchdog worker (scheduled by run_worker.py).

Usage:
    python -m app.services.jobs_watchdog_worker --once
    python -m app.services.jobs_watchdog_worker --once --json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging

from app.core.logging_config import configure_logging

logger = logging.getLogger(__name__)


async def _run(json_output: bool = False) -> None:
    from app.services.jobs_watchdog import run_jobs_watchdog_pass

    result = await run_jobs_watchdog_pass()
    if json_output:
        print(json.dumps(result, indent=2, default=str))
    else:
        from app.services.jobs_report import format_jobs_report

        print(format_jobs_report(result) if result.get("status") == "ok"
              else f"jobs watchdog: {result}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="run one pass and exit")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args()
    configure_logging()
    asyncio.run(_run(json_output=args.json))


if __name__ == "__main__":
    main()
