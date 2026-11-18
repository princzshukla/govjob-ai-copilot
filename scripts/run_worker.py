"""Hidden worker launcher for Windows Scheduled Tasks.

Why this exists: scheduled tasks must run invisibly (pythonw.exe, no console),
capture stdout/stderr/exceptions into log files, and never spawn two workers
at once. Normal CMD redirection would make a console window flash; doing the
redirection inside Python avoids that entirely.

Usage (started by Task Scheduler via pythonw.exe):
    pythonw.exe scripts/run_worker.py --worker poller
    pythonw.exe scripts/run_worker.py --worker layer2
"""
from __future__ import annotations

import argparse
import msvcrt
import os
import runpy
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
LOG_DIR = REPO_ROOT / "logs"

WORKERS = {
    "poller": (["-m", "app.services.layer1_poller", "--once"], LOG_DIR / "poller.log"),
    "layer2": (
        ["-m", "app.services.layer2_worker", "--all-sources", "--drain", "--max-docs", "50"],
        LOG_DIR / "layer2.log",
    ),
}


def _acquire_lock(name: str):
    """OS-level lock: released automatically when the process exits/crashes."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handle = open(LOG_DIR / f".{name}.lock", "a+b")
    handle.seek(0)
    try:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        handle.close()
        return None
    return handle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", choices=WORKERS)
    parser.add_argument("--self-test-exception", action="store_true",
                        help="write a deliberate traceback to logs/launcher-selftest.log and exit")
    args = parser.parse_args()
    if args.self_test_exception and not args.worker:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_DIR / "launcher-selftest.log", "a", encoding="utf-8") as fh:
            fh.write("\n%s exception-capture self-test\n" % datetime.now(timezone.utc).isoformat())
            try:
                raise RuntimeError("launcher exception capture self-test")
            except Exception:
                traceback.print_exc(file=fh)
        return 0
    if not args.worker:
        parser.error("--worker is required")

    os.chdir(BACKEND)
    sys.path.insert(0, str(BACKEND))

    lock = _acquire_lock(args.worker)
    if lock is None:
        return 0  # another instance is running — Task Scheduler will retry next tick

    module_args, log_path = WORKERS[args.worker]
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "a", encoding="utf-8", buffering=1)
    sys.stdout = log
    sys.stderr = log

    def excepthook(exc_type, exc, tb):
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        log.write(f"\n{ts} UNCAUGHT EXCEPTION in {args.worker}:\n")
        traceback.print_exception(exc_type, exc, tb, file=log)
        log.flush()

    sys.excepthook = excepthook

    try:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        log.write(f"\n{ts} === {args.worker} start (pid {os.getpid()}) ===\n")
        # The worker modules call logging.basicConfig/print; with stdout and
        # stderr already redirected, both land in the log file.
        sys.argv = [module_args[1]] + module_args[2:]
        runpy.run_module(module_args[1], run_name="__main__")
        log.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} === {args.worker} end ===\n")
        return 0
    except SystemExit as exc:
        return int(exc.code or 0)
    except Exception:
        traceback.print_exc(file=log)
        return 1
    finally:
        log.flush()
        log.close()
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
