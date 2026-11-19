"""Jobs Coverage Watchdog — dedicated, strict coverage monitor for live job
recruitment notifications.

Reuses the admit-card watchdog's proven primitives (parsing, normalization,
one-to-one assignment) but applies a strict 0.72 threshold plus job-specific
qualification/category signals. Discovery-only: nothing here publishes a job.
Unmatched entries are classified and handed to the shared discovery queue,
where only a human may approve an officially verified notification.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import date, datetime

import httpx

from app.services import coverage_watchdog as cw

logger = logging.getLogger(__name__)

# Strict, never lowered to manufacture coverage. The 0.55 default in the
# general coverage watchdog is deliberately NOT used for jobs.
JOBS_MATCH_THRESHOLD = 0.72
JOBS_WATCHDOG_INTERVAL_SECONDS = 24 * 3600
LOCK_NAME = "jobswatchdog"  # must match scripts/run_worker.py WORKERS key
_LOCK_PATH = None  # resolved lazily (logs dir may not exist at import time)

# Items that appear in a "latest jobs" feed but are not recruitment notices.
_NOT_JOB_RE = re.compile(
    r"result|answer key|admit card|hall ticket|exam city|city of examination|"
    r"date sheet|time ?table|syllabus|cut.?off|merit list|interview schedule|"
    r"document verification|dv schedule|mock test|exam calendar|postpon",
    re.IGNORECASE,
)

# Explicit aggregator -> curated seed aliases. Only exact normalized titles
# match; an alias is never inferred. Add a row here (with an official-source
# check) when editorial wording cannot be matched by the strong token set.
_JOB_TITLE_ALIASES: dict[str, str] = {
    cw.normalize_title("SSC CHSL 2026 Online Form"):
        cw.normalize_title("SSC Combined Higher Secondary Level (CHSL)"),
    cw.normalize_title("SSC CGL 2026 Online Form"):
        cw.normalize_title("SSC Combined Graduate Level (CGL)"),
    cw.normalize_title("RRB NTPC Undergraduate 2026 Online Form"):
        cw.normalize_title("RRB NTPC Undergraduate Posts (Clerk & Typist)"),
    cw.normalize_title("UPESSC TGT 2026 Online Form"):
        cw.normalize_title("UPESSC Assistant Teacher (TGT) 2026 — 17,735 posts (Advt 07/2026)"),
}

_QUALIFICATION_PATTERNS: dict[str, tuple[str, ...]] = {
    "class_10": (r"\b10\s*(?:th)?\b", r"matriculation", r"high school"),
    "class_12": (r"\b12\s*(?:th)?\b", r"intermediate", r"higher secondary"),
    "graduate": (r"graduate", r"bachelor", r"\bb\.?a\.?\b", r"\bb\.?com\b", r"\bb\.?sc\b"),
    "postgraduate": (r"post graduate", r"postgraduate", r"master'?s", r"\bm\.?a\.?\b"),
    "engineering": (r"engineer", r"\bb\.?tech\b", r"\bb\.?e\.?\b", r"diploma in engineering"),
    "medical": (r"mbbs", r"medical officer", r"nursing", r"pharmacy"),
    "iti": (r"\biti\b", r"trade apprentice", r"artisan"),
    "teacher": (r"teacher", r"\btgt\b", r"\bpgt\b", r"trained graduate", r"headmaster", r"principal"),
}
_CATEGORY_PATTERNS: dict[str, tuple[str, ...]] = {
    "banking": (r"\bbank\b", r"banking", r"\bibps\b", r"\brbi\b", r"\bsbi\b"),
    "railway": (r"\brrb\b", r"railway", r"loco pilot", r"apprentice"),
    "police": (r"police", r"constable", r"sub inspector", r"\bcapf", r"\bcisf\b", r"\bbsf\b"),
    "defence": (r"agniveer", r"\barmy\b", r"\bnavy\b", r"\bair force\b", r"defence"),
    "clerical": (r"clerk", r"assistant", r"stenographer", r"typist", r"junior secretariat"),
    "technical": (r"engineer", r"technician", r"junior engineer", r"scientist", r"programmer"),
    "teaching": (r"teacher", r"\btgt\b", r"\bpgt\b", r"professor", r"lecturer"),
    "apprentice": (r"apprentice", r"act apprentice", r"trade apprentice"),
}

# Classification values stored on the discovery queue.
CLASS_NEW = "new_recruitment"
CLASS_DUPLICATE = "duplicate"
CLASS_AMBIGUOUS = "ambiguous"
CLASS_IRRELEVANT = "irrelevant"
CLASS_VERIFY = "requires_official_verification"

_CANCEL_RE = re.compile(r"\b(cancelled|canceled|withdrawn|withdrawal|aborted)\b", re.I)
_REVISED_RE = re.compile(r"\b(revised|corrigendum|amendment|addendum|re-scheduled)\b", re.I)


def is_job_entry(entry: cw.CoverageEntry) -> bool:
    """Filter out non-recruitment items from the aggregator's jobs feed."""
    return not _NOT_JOB_RE.search(entry.title)


def _signals(title: str, patterns: dict[str, tuple[str, ...]]) -> set[str]:
    text = cw.normalize_title(title)
    return {
        key for key, regexes in patterns.items()
        if any(re.search(rx, text) for rx in regexes)
    }


def qualification_signals(title: str) -> set[str]:
    return _signals(title, _QUALIFICATION_PATTERNS)


def category_signals(title: str) -> set[str]:
    return _signals(title, _CATEGORY_PATTERNS)


def job_signal_penalty(a: str, b: str) -> float:
    """Admit-card signal penalty plus qualification/category agreement.

    Disagreement can only lower a score; it can never rescue a weak match.
    """
    score = cw.signal_penalty(a, b)
    if score <= -1.0:  # hard organization mismatch — do not soften it
        return score
    qa, qb = qualification_signals(a), qualification_signals(b)
    if qa and qb and not (qa & qb):
        score -= 0.25
    elif qa & qb:
        score += 0.05
    ca, cb = category_signals(a), category_signals(b)
    if ca and cb and not (ca & cb):
        score -= 0.2
    elif ca & cb:
        score += 0.05
    return score


def build_jobs_report(
    entries: list[cw.CoverageEntry],
    seed_titles: list[str],
    threshold: float = JOBS_MATCH_THRESHOLD,
    source_url: str = cw.LATEST_JOBS_URL,
    today: "date | None" = None,
) -> cw.CoverageReport:
    """Pure strict one-to-one matching — shared by network and offline callers."""
    entries = [e for e in entries if is_job_entry(e)]
    return cw.build_report(
        entries, seed_titles, threshold=threshold, source_url=source_url,
        actionable_only=True, today=today, kind="latest_jobs",
        aliases=_JOB_TITLE_ALIASES, penalty_fn=job_signal_penalty,
    )


def check_jobs_coverage(
    url: str = cw.LATEST_JOBS_URL,
    threshold: float = JOBS_MATCH_THRESHOLD,
) -> cw.CoverageReport:
    """Fetch the aggregator's jobs feed and build a strict one-to-one report."""
    with httpx.Client(timeout=cw.FETCH_TIMEOUT_SECONDS, follow_redirects=True,
                      headers={"User-Agent": cw.USER_AGENT}) as client:
        response = client.get(url)
        response.raise_for_status()
        page_html = response.text
    entries = [e for e in cw.parse_latest_jobs(page_html) if is_job_entry(e)]
    report = build_jobs_report(entries, cw.seed_titles(), threshold=threshold, source_url=url)
    if len(entries) < 5:
        logger.warning("jobs watchdog parsed only %d entries from %s — markup may have changed",
                       len(entries), url)
    return report


async def check_jobs_coverage_async(
    url: str = cw.LATEST_JOBS_URL,
    threshold: float = JOBS_MATCH_THRESHOLD,
) -> cw.CoverageReport:
    """Async variant used by the watchdog pass and the admin API."""
    page_html = await cw.fetch_latest_jobs_html(url)
    entries = [e for e in cw.parse_latest_jobs(page_html) if is_job_entry(e)]
    report = build_jobs_report(entries, cw.seed_titles(), threshold=threshold, source_url=url)
    if len(entries) < 5:
        logger.warning("jobs watchdog parsed only %d entries from %s — markup may have changed",
                       len(entries), url)
    return report


def classify_entry(
    entry: cw.CoverageEntry,
    *,
    analysis: dict,
    duplicate: dict | None = None,
    ambiguous: bool = False,
    verdict: dict | None = None,
) -> str:
    """One of the five discovery-queue classifications. Never an auto-publish."""
    if not is_job_entry(entry):
        return CLASS_IRRELEVANT
    if ambiguous:
        return CLASS_AMBIGUOUS
    if duplicate and duplicate.get("is_duplicate"):
        return CLASS_DUPLICATE
    if not analysis.get("organization") or len(analysis.get("organization_candidates") or []) > 1:
        return CLASS_VERIFY
    if verdict and verdict.get("reachable") and verdict.get("is_pdf") and verdict.get("document_matched"):
        return CLASS_NEW
    return CLASS_VERIFY


# --- Official PDF field extraction (deterministic; no aggregator text ever used) ---

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_DMY_RE = re.compile(r"\b(\d{1,2})[.\-/](\d{1,2})[.\-/]((?:19|20)\d{2})\b")
_MONTH_RE = re.compile(r"\b(\d{1,2})\s+([A-Za-z]+)\s+((?:19|20)\d{2})\b")


def parse_official_date(text: str | None) -> date | None:
    if not text:
        return None
    candidates: list[tuple[int, date]] = []
    for match in _DMY_RE.finditer(text):
        d, m, y = match.groups()
        try:
            candidates.append((match.start(), date(int(y), int(m), int(d))))
        except ValueError:
            continue
    for match in _MONTH_RE.finditer(text):
        d, month, y = match.groups()
        month_no = _MONTHS.get(month.lower())
        if month_no:
            try:
                candidates.append((match.start(), date(int(y), month_no, int(d))))
            except ValueError:
                continue
    if not candidates:
        return None
    # Earliest date in the label window wins, regardless of its format.
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _window(text: str, labels: tuple[str, ...], span: int = 180) -> str:
    for label in labels:
        match = re.search(label, text, re.I)
        if match:
            return text[match.end():match.end() + span]
    return ""


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def extract_job_fields(text: str) -> dict:
    """Extract recruitment facts directly from official notification text.

    Missing values stay ``None`` — they are never inferred from the aggregator
    or invented by a language model. Returned dates are ISO strings so the
    dict can be stored straight into ``extracted_information`` (JSONB).
    """
    start = parse_official_date(_window(text, (
        r"start(?:ing)?\s+date", r"date\s+of\s+(?:commencement|opening)",
        r"application\s+(?:start|begin)", r"online\s+application\s+(?:from|starts?)",
    )))
    closing = parse_official_date(_window(text, (
        r"last\s+date", r"closing\s+date", r"last\s+date\s+for\s+(?:online\s+)?(?:application|submission)",
    )))
    vacancies_match = re.search(
        r"(?:total\s*)?(?:no\.?\s*of\s*)?vacanc(?:y|ies)\s*[:\-]?\s*([\d,]+)",
        text, re.I,
    )
    vacancies = int(vacancies_match.group(1).replace(",", "")) if vacancies_match else None
    age_match = re.search(r"\b(\d{1,2})\s*(?:to|-|–)\s*(\d{1,2})\s*(?:years|yrs)",
                          _window(text, (r"age\s+limit", r"age"), 200), re.I)
    qualification = _window(text, (r"educational\s+qualification", r"qualification"), 160).strip()
    return {
        "application_start_date": _iso(start),
        "application_last_date": _iso(closing),
        "total_vacancies": vacancies,
        "min_age": int(age_match.group(1)) if age_match else None,
        "age_max_general": int(age_match.group(2)) if age_match else None,
        "required_qualification": (qualification[:160] or None),
        "cancelled": bool(_CANCEL_RE.search(text)),
        "revised": bool(_REVISED_RE.search(text)),
    }


async def verify_job_notification(url: str, title: str, client: httpx.AsyncClient) -> dict:
    """Official-domain verification with PDF fact extraction.

    Thin adapter over ``discovery_engine.verify_official_candidate``: the
    aggregator title is only a lead; evidence is the official URL and, when it
    is a PDF, text read directly from that PDF.
    """
    from app.services import discovery_engine as de

    result = await de.verify_official_candidate(url, title, client)
    result["fields"] = {}
    if not (result.get("reachable") and result.get("is_pdf") and result.get("document_matched")):
        return result
    try:
        response = await client.get(url, timeout=25)
        response.raise_for_status()
        from app.services import notification_extractor as nx

        text, _pages, _cpp = nx.extract_text_stats(response.content)
        result["fields"] = extract_job_fields(text)
    except Exception:
        logger.exception("official PDF field extraction failed for %s", url)
    return result


def classification_for_report_entry(entry: cw.CoverageEntry, report: cw.CoverageReport) -> str:
    ambiguous = any(e.url == entry.url for e, _seed, _score in report.ambiguous)
    if ambiguous:
        return CLASS_AMBIGUOUS
    return CLASS_VERIFY


# --- process/lock orchestration -------------------------------------------------

def _lock_path():
    global _LOCK_PATH
    if _LOCK_PATH is None:
        from pathlib import Path

        _LOCK_PATH = Path(__file__).resolve().parents[3] / "logs" / f".{LOCK_NAME}.lock"
    return _LOCK_PATH


def try_acquire_lock():
    """Cross-process lock shared with the scheduled worker launcher."""
    try:
        import msvcrt

        path = _lock_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(path, "a+b")
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            handle.close()
            return None
        return handle
    except ImportError:  # pragma: no cover - non-Windows fallback
        return _try_fcntl_lock()


def _try_fcntl_lock():  # pragma: no cover - Linux dev/CI convenience
    import fcntl

    path = _lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "a+b")
    try:
        fcntl.lockf(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def release_lock(handle) -> None:
    if handle is None:
        return
    try:
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    except ImportError:  # pragma: no cover
        import fcntl

        fcntl.lockf(handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass
    finally:
        handle.close()


async def run_jobs_discovery(db, report: cw.CoverageReport) -> dict:
    """Feed genuinely unmatched jobs into the shared discovery queue."""
    from app.services import discovery_engine as de

    return await de.run_discovery(
        db,
        report.missing,
        notification_kind="job",
        classification_fn=lambda entry: classification_for_report_entry(entry, report),
        verifier=verify_job_notification,
    )


async def run_jobs_watchdog_pass() -> dict:
    """One full pass: coverage -> discovery -> deadlines -> report."""
    lock = try_acquire_lock()
    if lock is None:
        logger.info("jobs watchdog skipped — another instance holds the lock")
        return {"skipped": True, "reason": "already_running"}
    started = datetime.now()
    logger.info("jobs watchdog pass started at %s", started.isoformat(timespec="seconds"))
    try:
        from app.core.database import AsyncSessionLocal
        from app.services import job_deadline_watchdog as jdw
        from app.services import jobs_report

        report = await check_jobs_coverage_async()
        async with AsyncSessionLocal() as db:
            discovery_stats = await run_jobs_discovery(db, report)
            deadline_stats = await jdw.check_exam_deadlines(db)
            data = await jobs_report.build_jobs_watchdog_report(
                db, report, discovery_stats, deadline_stats
            )
        text = jobs_report.format_jobs_report(data)
        logger.info("jobs watchdog pass completed:\n%s", text)
        try:
            await cw.send_watchdog_alert(report)
        except Exception:
            logger.exception("jobs watchdog alert failed")
        return data
    except Exception:
        logger.exception("jobs watchdog pass failed")
        return {"status": "failed"}
    finally:
        release_lock(lock)


async def jobs_watchdog_loop(interval_seconds: int = JOBS_WATCHDOG_INTERVAL_SECONDS) -> None:
    while True:
        await run_jobs_watchdog_pass()
        await asyncio.sleep(interval_seconds)
