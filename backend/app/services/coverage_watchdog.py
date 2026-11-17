"""Coverage watchdog — find live jobs listed by the curated aggregator
(sarkariresult.com.cm) that are missing from our seed data.

Why this exists: Sarkari Result keeps its "Latest Jobs" page editorially
up to date; our seed file (``app/core/seed.py``) is only as fresh as the last
human edit. This watchdog fetches the aggregator's public latest-jobs listing
(read-only, one page per run), fuzzy-matches the titles against
``SEED_EXAMS`` and reports which live entries we do not carry.

Design rules:

* **Discovery only, never auto-publish.** Titles here are untrusted
  third-party editorial work; every missing job must be added to the seed by
  a human, sourced from the *official* notification PDF — never copied from
  the aggregator.
* **Fail soft.** Network errors, markup changes or empty parses are logged
  and swallowed by the loop; they must never crash the app.
* One page per run, weekly, with an identifying User-Agent — we are a guest
  on that site, not a scraper fleet.
"""
from __future__ import annotations

import asyncio
import html
import logging
import re
from dataclasses import dataclass
from difflib import SequenceMatcher

import httpx

logger = logging.getLogger(__name__)

LATEST_JOBS_URL = "https://sarkariresult.com.cm/latest-jobs/"
ADMIT_CARD_URL = "https://sarkariresult.com.cm/admit-card/"
ADMIT_CARD_MATCH_THRESHOLD = 0.5
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 "
    "GovJobMatcher-coverage-watchdog/1.0"
)
DEFAULT_MATCH_THRESHOLD = 0.55
FETCH_TIMEOUT_SECONDS = 30.0
_WATCHDOG_INTERVAL_SECONDS = 7 * 24 * 3600

_LIST_BLOCK_RE = re.compile(
    r'<ul[^>]*class="[^"]*latest-posts-last-date[^"]*"[^>]*>(.*?)</ul>', re.S
)
_ITEM_RE = re.compile(r"<li>\s*<a[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>(.*?)</li>", re.S)
_LAST_DATE_RE = re.compile(r"Last\s*Date\s*:?\s*([^<]+)", re.I)
_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class CoverageEntry:
    title: str
    url: str
    last_date: str | None


def parse_last_date(text: str | None) -> "date | None":
    """Parse '06 December 2026'-style last dates; returns None otherwise."""
    from datetime import datetime

    if not text:
        return None
    cleaned = " ".join(text.replace(".", " ").split())
    # tolerate a doubled 'Last Date :' prefix that slipped through
    cleaned = re.sub(r"(?i)^last\s*date\s*:?\s*", "", cleaned)
    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def is_actionable(entry: CoverageEntry, today: "date | None" = None) -> bool:
    """True when the entry carries a parseable last date still in the future
    (or today, IST). Entries without one are the site's stale 2025 archive
    links — noise for coverage purposes."""
    from app.core.timeutils import today_ist

    deadline = parse_last_date(entry.last_date)
    if deadline is None:
        return False
    return deadline >= (today or today_ist())


@dataclass
class CoverageReport:
    source_url: str
    entries: list[CoverageEntry]
    matched: list[tuple[CoverageEntry, str, float]]
    missing: list[CoverageEntry]
    seed_count: int
    filtered_out: int = 0
    kind: str = "latest_jobs"

    @property
    def coverage_pct(self) -> float:
        if not self.entries:
            return 0.0
        return round(100.0 * len(self.matched) / len(self.entries), 1)


def _strip_html(fragment: str) -> str:
    return " ".join(html.unescape(_TAG_RE.sub("", fragment)).split())


def parse_latest_jobs(page_html: str) -> list[CoverageEntry]:
    """Parse the ``<ul class="latest-posts-last-date">`` block into entries.

    Falls back to scanning the whole document if the wrapper class is absent
    (the site can rename it); entries without a "Last Date" suffix are still
    returned with ``last_date=None``.
    """
    block = _LIST_BLOCK_RE.search(page_html)
    scope = block.group(1) if block else page_html
    entries: list[CoverageEntry] = []
    for href, raw_title, rest in _ITEM_RE.findall(scope):
        title = _strip_html(raw_title)
        if len(title) < 10:
            continue
        match = _LAST_DATE_RE.search(_strip_html(rest))
        last_date = " ".join(match.group(1).split()) if match else None
        entries.append(CoverageEntry(title=title, url=href, last_date=last_date))
    return entries


_ADMIT_HEADING_RE = re.compile(r"All Latest Admit Card", re.I)
_ADMIT_ITEM_RE = re.compile(
    r'<a[^>]*class="[^"]*latest-posts__post-title[^"]*"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>',
    re.S,
)

def parse_admit_cards_page(page_html: str) -> list[CoverageEntry]:
    """Parse the 'All Latest Admit Card' list (plain links, no last dates).

    Scoped to the section after the 'All Latest Admit Card' heading so
    sidebar/footer link lists are not picked up.
    """
    match = _ADMIT_HEADING_RE.search(page_html)
    rest = page_html[match.end():] if match else page_html
    list_match = re.search(r'<ul[^>]*latest-posts__list[^>]*>(.*?)</ul>', rest, re.S)
    scope = list_match.group(1) if list_match else rest
    entries: list[CoverageEntry] = []
    for href, raw_title in _ADMIT_ITEM_RE.findall(scope):
        title = _strip_html(raw_title)
        if len(title) < 10:
            continue
        entries.append(CoverageEntry(title=title, url=href, last_date=None))
    return entries


def normalize_title(title: str) -> str:
    text = html.unescape(title).lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return " ".join(text.split())


def match_score(normalized_a: str, normalized_b: str) -> float:
    """Blend edit-distance ratio with token-set Jaccard (scaled).

    Token overlap dominates for reordered/verbose titles ("UPESSC UP TGT
    Online Form 2026 (17,735 Posts)" vs "UPESSC Assistant Teacher (TGT) 2026
    — 17,735 posts"); SequenceMatcher catches near-identical strings.
    """
    seq = SequenceMatcher(None, normalized_a, normalized_b).ratio()
    set_a, set_b = set(normalized_a.split()), set(normalized_b.split())
    jaccard = len(set_a & set_b) / max(1, len(set_a | set_b))
    return max(seq, jaccard * 1.4)


def build_report(
    entries: list[CoverageEntry],
    seed_titles: list[str],
    threshold: float = DEFAULT_MATCH_THRESHOLD,
    source_url: str = LATEST_JOBS_URL,
    actionable_only: bool = False,
    today: "date | None" = None,
    kind: str = "latest_jobs",
) -> CoverageReport:
    filtered_out = 0
    if actionable_only:
        actionable = [e for e in entries if is_actionable(e, today)]
        filtered_out = len(entries) - len(actionable)
        entries = actionable
    normalized_seeds = [normalize_title(t) for t in seed_titles]
    matched: list[tuple[CoverageEntry, str, float]] = []
    missing: list[CoverageEntry] = []
    for entry in entries:
        normalized_entry = normalize_title(entry.title)
        best_score, best_seed = 0.0, ""
        for seed_title, normalized_seed in zip(seed_titles, normalized_seeds):
            score = match_score(normalized_entry, normalized_seed)
            if score > best_score:
                best_score, best_seed = score, seed_title
        if best_score >= threshold:
            matched.append((entry, best_seed, best_score))
        else:
            missing.append(entry)
    return CoverageReport(
        source_url=source_url,
        entries=entries,
        matched=matched,
        missing=missing,
        seed_count=len(seed_titles),
        filtered_out=filtered_out,
        kind=kind,
    )


def seed_titles() -> list[str]:
    from app.core.seed import SEED_EXAMS  # lazy: seed.py is ~2k lines

    return [str(item.get("title", "")) for item in SEED_EXAMS if item.get("title")]


def seed_admit_titles() -> list[str]:
    from app.core.admit_cards import SEED_ADMIT_CARDS

    return [str(item.get("title", "")) for item in SEED_ADMIT_CARDS if item.get("title")]


async def fetch_latest_jobs_html(
    url: str = LATEST_JOBS_URL, timeout: float = FETCH_TIMEOUT_SECONDS
) -> str:
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


async def check_coverage(
    url: str = LATEST_JOBS_URL,
    threshold: float = DEFAULT_MATCH_THRESHOLD,
    actionable_only: bool = True,
    kind: str = "latest_jobs",
) -> CoverageReport:
    page_html = await fetch_latest_jobs_html(url)
    if kind == "admit_card":
        entries = parse_admit_cards_page(page_html)
        report = build_report(
            entries,
            seed_admit_titles(),
            threshold=ADMIT_CARD_MATCH_THRESHOLD,
            source_url=url,
            actionable_only=False,  # admit list carries no dates
            kind="admit_card",
        )
    else:
        entries = parse_latest_jobs(page_html)
        report = build_report(
            entries,
            seed_titles(),
            threshold=threshold,
            source_url=url,
            actionable_only=actionable_only,
        )
    if len(entries) < 5:
        # A parse that suddenly finds almost nothing means the site changed
        # markup — surface that loudly instead of "0 missing, all good".
        logger.warning(
            "coverage watchdog parsed only %d entries from %s — markup may have changed",
            len(entries),
            url,
        )
    return report


def format_report(report: CoverageReport, limit: int = 60) -> str:
    label = "Admit-card coverage watchdog" if report.kind == "admit_card" else "Coverage watchdog"
    unit = "admit cards" if report.kind == "admit_card" else "live entries"
    skipped = f" | stale/archived skipped: {report.filtered_out}" if report.filtered_out else ""
    lines = [
        f"{label} — {report.source_url}",
        (
            f"{unit}: {len(report.entries)}{skipped} | seed rows: {report.seed_count} | "
            f"matched: {len(report.matched)} ({report.coverage_pct}%) | "
            f"missing: {len(report.missing)}"
        ),
        "",
    ]
    if report.missing:
        lines.append("Missing from seed — source each from the OFFICIAL PDF, never by copying:")
        for entry in report.missing[:limit]:
            lines.append(
                f"- {entry.title} | last date: {entry.last_date or 'n/a'} | {entry.url}"
            )
        if len(report.missing) > limit:
            lines.append(f"… and {len(report.missing) - limit} more")
    else:
        lines.append("Every live entry is represented in the seed.")
    return "\n".join(lines)


async def send_watchdog_alert(report: CoverageReport) -> bool:
    from app.core.config import settings
    from app.services.notifier import send_telegram_alert

    if not report.missing:
        return True
    text = format_report(report)
    if not settings.TELEGRAM_ADMIN_CHAT_ID:
        logger.info("admin chat not configured; watchdog report not sent:\n%s", text)
        return False
    return await send_telegram_alert(settings.TELEGRAM_ADMIN_CHAT_ID, text)


async def coverage_watchdog_loop(interval_seconds: int = _WATCHDOG_INTERVAL_SECONDS) -> None:
    """Weekly in-process watchdog; safe to run from every worker (read-only
    fetch + an admin alert; no writes to the database)."""
    while True:
        for kind, url in (("latest_jobs", LATEST_JOBS_URL), ("admit_card", ADMIT_CARD_URL)):
            try:
                report = await check_coverage(url, kind=kind)
                if report.missing:
                    logger.warning(
                        "coverage watchdog (%s): %d entries missing from seed",
                        kind,
                        len(report.missing),
                    )
                    await send_watchdog_alert(report)
                else:
                    logger.info(
                        "coverage watchdog (%s): all %d entries covered by the seed",
                        kind,
                        len(report.entries),
                    )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("coverage watchdog pass failed (%s)", kind)
        await asyncio.sleep(interval_seconds)
