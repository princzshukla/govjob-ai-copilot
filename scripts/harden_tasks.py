"""Harden existing GovJob Scheduled Tasks for unattended background runs.

Preserves the task name and schedule (exported via schtasks /XML) and patches:
  - MultipleInstancesPolicy = IgnoreNew (no overlapping workers)
  - DisallowStartIfOnBatteries / StopIfGoingOnBatteries = false
  - StartWhenAvailable = true
  - ExecutionTimeLimit = PT0S (unlimited)
Drops any top-level <Hidden> node (not valid in Task Scheduler 1.2).

Usage: python scripts/harden_tasks.py
"""
import re
import subprocess
import tempfile
from pathlib import Path


def harden(name: str) -> None:
    raw = subprocess.check_output(["schtasks", "/Query", "/TN", name, "/XML"])
    bom = raw[:2] in (bytes([255, 254]), bytes([254, 255]))
    xml = raw.decode("utf-16" if bom else "utf-8")

    replacements = {
        "<DisallowStartIfOnBatteries>true</DisallowStartIfOnBatteries>":
            "<DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>",
        "<StopIfGoingOnBatteries>true</StopIfGoingOnBatteries>":
            "<StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>",
        "<MultipleInstancesPolicy>AllowMultiple</MultipleInstancesPolicy>":
            "<MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>",
        "<StartWhenAvailable>false</StartWhenAvailable>":
            "<StartWhenAvailable>true</StartWhenAvailable>",
        "<ExecutionTimeLimit>PT72H</ExecutionTimeLimit>":
            "<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>",
    }
    for old, new in replacements.items():
        xml = xml.replace(old, new)
    if "<StartWhenAvailable>" not in xml:
        xml = xml.replace("<Settings>", "<Settings>\n      <StartWhenAvailable>true</StartWhenAvailable>")

    xml = re.sub(r"\s*<Hidden>.*?</Hidden>", "", xml)

    path = Path(tempfile.gettempdir()) / f"{name}.xml"
    path.write_text(xml, encoding="utf-16")  # declaration says UTF-16; include BOM
    subprocess.run(
        ["schtasks", "/Create", "/TN", name, "/XML", str(path), "/F"],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    print(f"hardened {name}")


if __name__ == "__main__":
    for task in ("GovJob-Poller", "GovJob-Layer2"):
        harden(task)
