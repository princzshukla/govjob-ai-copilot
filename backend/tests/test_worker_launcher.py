"""Scheduled-task launcher contract (offline)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import run_worker  # noqa: E402


def test_worker_contract():
    poller_args, poller_log = run_worker.WORKERS["poller"]
    layer2_args, layer2_log = run_worker.WORKERS["layer2"]

    assert poller_args == ["-m", "app.services.layer1_poller", "--once"]
    assert poller_log.name == "poller.log"
    assert layer2_args == [
        "-m", "app.services.layer2_worker",
        "--all-sources", "--drain", "--max-docs", "50",
    ]
    assert layer2_log.name == "layer2.log"
    assert run_worker.BACKEND.name == "backend"
    assert run_worker.LOG_DIR.name == "logs"


def test_exception_self_test_writes_traceback(tmp_path):
    import subprocess

    pyw = run_worker.BACKEND / "venv312" / "Scripts" / "pythonw.exe"
    if not pyw.exists():
        return  # skip on machines without pythonw
    before = run_worker.LOG_DIR / "launcher-selftest.log"
    old = before.read_text(encoding="utf-8") if before.exists() else ""
    subprocess.run([str(pyw), str(Path(run_worker.__file__)), "--self-test-exception"], check=True)
    new = before.read_text(encoding="utf-8")
    assert new[len(old):].count("Traceback") >= 1
