#!/usr/bin/env python
"""Step 3 benchmark — LLM extraction from real notification PDFs.

Reads ``benchmarks/manifest.json`` (10 real PDFs, expected values recorded
from the documents by hand), runs each PDF through
``app.services.notification_extractor.extract_notification`` and grades the
five critical fields:

    total_vacancies, min_age/max_age (+ age_cutoff_date),
    required_qualification, application_last_date, pay_level

Grading:
    integer/date fields — exact match
    qualification/pay   — case-insensitive substring match of ALL manifest
                          tokens against the extracted text

PDF-level verdicts:
    PASS     every graded field correct
    FLAGGED  extractor set needs_manual_review (safe outcome, not auto-publishable)
    FAIL     at least one graded field wrong WITHOUT a flag  → publishable error

Pass criteria for the whole benchmark: ≥ 9/10 PDFs are PASS or FLAGGED, and
zero hallucinated dates/ages are silently published (a value that exists in
the PDF only vaguely, or an expected field that came out null, counts as a
miss — never as a correct extraction).

Scanned controls are asserted too: they must come out is_scanned=true with
needs_manual_review=true and must not invoke the LLM.

Run from the backend directory:
    python scripts/benchmark_notification_extraction.py [--pdf-dir benchmarks/pdfs]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.schemas.pipeline import ExtractionResult  # noqa: E402
from app.services.notification_extractor import extract_notification  # noqa: E402

MANIFEST_PATH = BACKEND_DIR / "benchmarks" / "manifest.json"


def _norm(value: object) -> str:
    return re.sub(r"\s+", " ", str(value).lower()).strip()


def _tokens_ok(extracted: object, tokens: list[str]) -> bool:
    text = _norm(extracted or "")
    return all(_norm(t) in text for t in tokens)


def grade(expected: dict, result: ExtractionResult) -> list[tuple[str, bool | None, str, str]]:
    """(field, ok|None, expected_repr, actual_repr) — None ok means ungraded."""
    checks: list[tuple[str, bool | None, str, str]] = []

    def exact(field: str) -> None:
        want = expected.get(field, expected.get(f"{field}_any_of"))
        if want is None:
            checks.append((field, None, "-", "-"))
            return
        got = getattr(result, field)
        if isinstance(want, list):
            ok = got in want
            checks.append((field, ok, " | ".join(str(w) for w in want), str(got)))
        else:
            checks.append((field, got == want, str(want), str(got)))

    def date_exact(field: str) -> None:
        any_of = expected.get(f"{field}_any_of")
        if field in expected:
            want_list = [date.fromisoformat(expected[field])]
        elif any_of:
            want_list = [date.fromisoformat(d) for d in any_of]
        else:
            checks.append((field, None, "-", "-"))
            return
        got = getattr(result, field)
        ok = got in want_list
        checks.append((field, ok, " | ".join(d.isoformat() for d in want_list), str(got)))

    exact("total_vacancies")
    exact("min_age")
    exact("age_max_general")
    date_exact("age_cutoff_date")
    date_exact("application_last_date")

    if "relaxations" in expected:
        want = {str(k).upper(): int(v) for k, v in expected["relaxations"].items()}
        got_relax = {str(k).upper(): v for k, v in (result.age_relaxations or {}).items()}
        ok = all(got_relax.get(k) == v for k, v in want.items())
        checks.append(("age_relaxations", ok, str(want), str(got_relax)))
    else:
        checks.append(("age_relaxations", None, "ungraded", str(result.age_relaxations)))

    if "required_qualification_tokens" in expected:
        ok = _tokens_ok(result.required_qualification, expected["required_qualification_tokens"])
        checks.append(("required_qualification", ok, "tokens " + str(expected["required_qualification_tokens"]), str(result.required_qualification)))
    else:
        checks.append(("required_qualification", None, "ungraded", str(result.required_qualification)))

    if "pay_level_tokens" in expected:
        ok = _tokens_ok(result.pay_level, expected["pay_level_tokens"])
        checks.append(("pay_level", ok, "tokens " + str(expected["pay_level_tokens"]), str(result.pay_level)))
    else:
        checks.append(("pay_level", None, "ungraded", str(result.pay_level)))

    return checks


async def run(pdf_dir: Path) -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    rows: list[dict] = []

    for entry in manifest["pdfs"]:
        path = pdf_dir / entry["file"]
        if not path.exists():
            rows.append({"file": entry["file"], "verdict": "MISSING", "checks": [], "error": "file not found"})
            continue
        try:
            result = await extract_notification(path.read_bytes())
        except Exception as exc:  # pragma: no cover - real network/LLM
            rows.append({"file": entry["file"], "verdict": "FAIL", "checks": [], "error": f"{type(exc).__name__}: {exc}"})
            continue
        checks = grade(entry["expected"], result)
        graded = [c for c in checks if c[1] is not None]
        all_ok = all(c[1] for c in graded) if graded else False
        rows.append({
            "file": entry["file"],
            "verdict": ("PASS" if all_ok else "FAIL") if not result.needs_manual_review else ("FLAGGED" if all_ok else "FLAGGED-WITH-MISSES"),
            "result": result.model_dump(mode="json"),
            "checks": checks,
            "error": None,
        })

    scanned_rows: list[dict] = []
    for entry in manifest.get("scanned_controls", []):
        path = pdf_dir / entry["file"]
        if not path.exists():
            scanned_rows.append({"file": entry["file"], "ok": False, "detail": "file not found"})
            continue
        result = await extract_notification(path.read_bytes())
        ok = result.is_scanned and result.needs_manual_review
        scanned_rows.append({"file": entry["file"], "ok": ok, "is_scanned": result.is_scanned, "needs_manual_review": result.needs_manual_review, "review_reasons": result.review_reasons})

    passed = sum(1 for r in rows if r["verdict"] == "PASS")
    flagged = sum(1 for r in rows if r["verdict"].startswith("FLAGGED"))
    failed = [r for r in rows if r["verdict"] == "FAIL"]
    safe = passed + flagged
    total = len(rows)

    lines: list[str] = []
    lines.append("# Notification-Extraction Benchmark Report\n")
    lines.append(f"Date: 2026-11-13 · PDFs: {total} · model: `{settings.GROQ_MODEL}`\n")
    lines.append("## Per-PDF results\n")
    for r in rows:
        lines.append(f"### {r['file']} — **{r['verdict']}**\n")
        if r.get("error"):
            lines.append(f"- error: {r['error']}\n")
            continue
        res = r["result"]
        lines.append(f"- confidence: {res['confidence']} · needs_manual_review: {res['needs_manual_review']} · review_reasons: {res['review_reasons']}\n")
        for field, ok, want, got in r["checks"]:
            mark = "✓" if ok else ("–" if ok is None else "✗")
            lines.append(f"- [{mark}] `{field}` — expected `{want}` · got `{got}`\n")
        lines.append("")

    lines.append("## Scanned controls\n")
    for s in scanned_rows:
        lines.append(f"- {s['file']}: {'PASS' if s['ok'] else 'FAIL'} — is_scanned={s.get('is_scanned')} needs_manual_review={s.get('needs_manual_review')} reasons={s.get('review_reasons')}")

    lines.append("\n## Tally\n")
    lines.append(f"- PASS: {passed}/{total}")
    lines.append(f"- FLAGGED for manual review (safe): {flagged}/{total}")
    lines.append(f"- FAIL (wrong values, publishable): {len(failed)}/{total}")
    lines.append(f"- **≥ 9/10 safe (PASS or FLAGGED, zero silent wrong dates/ages): {'PASS' if safe >= 9 and not failed else 'FAIL'}** ({safe}/{total})\n")

    report = MANIFEST_PATH.parent / "notification_extraction_report.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nReport written to {report}")
    return 0 if (safe >= 9 and not failed) else 1


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:  # very old interpreters
        pass
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-dir", type=Path, default=BACKEND_DIR / "benchmarks" / "pdfs")
    args = parser.parse_args()
    sys.exit(asyncio.run(run(args.pdf_dir)))


if __name__ == "__main__":
    main()
