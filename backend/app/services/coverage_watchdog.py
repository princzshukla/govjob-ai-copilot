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
from dataclasses import dataclass, field
from difflib import SequenceMatcher

import httpx

logger = logging.getLogger(__name__)

LATEST_JOBS_URL = "https://sarkariresult.com.cm/latest-jobs/"
ADMIT_CARD_URL = "https://sarkariresult.com.cm/admit-card/"
ADMIT_CARD_MATCH_THRESHOLD = 0.72
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
    # One-to-one reporting: one seed can cover at most one aggregator entry.
    distinct_matched_seeds: list[str] = field(default_factory=list)
    ambiguous: list[tuple[CoverageEntry, str, float]] = field(default_factory=list)
    duplicate_matches: dict[str, list[str]] = field(default_factory=dict)

    @property
    def coverage_pct(self) -> float:
        if not self.entries:
            return 0.0
        return round(100.0 * len(self.matched) / len(self.entries), 1)

    @property
    def distinct_seed_pct(self) -> float:
        if not self.seed_count:
            return 0.0
        return round(100.0 * len(self.distinct_matched_seeds) / self.seed_count, 1)


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
# Items their "Admit Card" page lumps in that are NOT admit cards.
_NOT_ADMIT_RE = re.compile(
    r"exam calendar|date sheet|time table|timetable|postpon|postpn|dv schedule|document verification schedule|result|answer key|cut.?off|syllabus|notification out",
    re.IGNORECASE,
)
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
        if _NOT_ADMIT_RE.search(title):
            continue
        entries.append(CoverageEntry(title=title, url=href, last_date=None))
    return entries


# Titles where the aggregator's wording is too different from our curated
# title for token matching (same official notice, already seeded).
_TITLE_ALIASES = {
    "ssc cpo si capf paper i exam city details 2026":
        "ssc sub inspector in delhi police capfs 2025 paper i city of examination admission certificate",
    # Seed carries the advertisement year (2025) while the aggregator uses the
    # exam year (2026); explicit alias keeps this legitimate coverage.
    "rrb ntpc 10 2 ug cbtst exam city details 2026":
        "rrb ntpc ug cen 07 2025 cbtst exam city admit card",
}
_ALIAS_MATCH_SCORE = 1.0  # explicit aliases bypass fuzzy scoring/year mismatch

# Filler tokens that do not identify a notice. Removed in strong mode only,
# so legacy normalize_title() stays backward-compatible.
_FILLER_TOKENS = {
    "online", "form", "forms", "notification", "notifications", "download",
    "link", "links", "out", "the", "of", "for", "and", "advt", "no", "regarding",
    "information", "candidates", "candidate", "important", "latest", "exam",
    "examination", "details", "issue", "released", "release", "date", "dates",
}
_YEAR_RE = re.compile(r"\b20\d{2}\b")

# Organization signals: a title is tagged with the canonical boards it names.
# Both sides must be tagged AND disjoint to count as a hard mismatch.
_ORG_PATTERNS: dict[str, tuple[str, ...]] = {
    "ssc": (r"\bssc\b", r"staff selection commission"),
    "upsc": (r"\bupsc\b", r"union public service commission"),
    "upsssc": (r"\bupsssc\b", r"subordinate services selection commission"),
    "uppsc": (r"\buppsc\b", r"up public service commission"),
    "upessc": (r"\bupessc\b", r"up secondary education"),
    "ibps": (r"\bibps\b", r"institute of banking personnel selection"),
    "sbi": (r"\bsbi\b", r"state bank of india"),
    "rrb": (r"\brrb\b", r"railway recruitment board"),
    "rssb": (r"\brssb\b", r"rajasthan staff selection board"),
    "iim": (r"\biim\b", r"\bcat\b"),
    "mphc": (r"\bmphc\b", r"\bmp\b.*\bhigh court\b", r"madhya pradesh high court"),
    "allhc": (r"allahabad high court", r"\ballhc\b"),
    "dhc": (r"delhi high court", r"\bdhc\b"),
    "bpsc": (r"\bpsc\b", r"bihar public service commission"),
    "cgpsc": (r"\bcgpsc\b", r"chhattisgarh public service commission"),
    "mppsc": (r"\bmppsc\b", r"madhya pradesh public service commission"),
    "ctet": (r"\bctet\b", r"teacher eligibility test"),
    "navy": (r"\bnavy\b", r"agniveer"),
    "cisf": (r"\bcisf\b", r"central industrial security force"),
    "bsf": (r"\bbsf\b", r"border security force"),
    "ssb": (r"\bssb\b", r"sashastra seema bal"),
    "skau": (r"\bskau\b", r"kurukshetra"),
    "upcisb": (r"\bupcisb\b", r"cooperative institutional service board"),
    "bob": (r"bank of baroda", r"\bbob\b"),
    "iob": (r"indian overseas bank", r"\biob\b"),
    "nicl": (r"\bnicl\b", r"national insurance"),
    "kvs": (r"\bkvs\b", r"kendriya vidyalaya"),
    "nvs": (r"\bnvs\b", r"navodaya vidyalaya"),
}
_SUBTYPE_PATTERNS: dict[str, tuple[str, ...]] = {
    "exam_city": (r"exam city", r"city of examination", r"exam centre", r"centre of examination"),
    "admit_card": (r"admit card", r"e admit card", r"hall ticket", r"admission certificate"),
    "interview": (r"interview", r"call letter"),
    "exam_date": (r"exam date", r"pre exam", r"schedule", r"timetable"),
}

def normalize_title(title: str) -> str:
    text = html.unescape(title).lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return " ".join(text.split())


def normalize_strong(title: str) -> str:
    """Aggressive normalization: drop filler words and standalone years.

    Both years and organization are checked separately as signals, so they
    are removed from the fuzzy token set to stop them dominating similarity.
    """
    tokens = normalize_title(title).split()
    return " ".join(
        t for t in tokens if t not in _FILLER_TOKENS and not _YEAR_RE.fullmatch(t)
    )


def org_signals(title: str) -> set[str]:
    text = normalize_title(title)
    return {
        org
        for org, patterns in _ORG_PATTERNS.items()
        if any(re.search(pattern, text) for pattern in patterns)
    }


def year_signals(title: str) -> set[str]:
    return set(_YEAR_RE.findall(title))


def subtype_signals(title: str) -> set[str]:
    text = normalize_title(title)
    return {
        subtype
        for subtype, patterns in _SUBTYPE_PATTERNS.items()
        if any(re.search(pattern, text) for pattern in patterns)
    }


def signal_penalty(a: str, b: str) -> float:
    """Signal disagreement penalty (negative) or agreement bonus (positive)."""
    oa, ob = org_signals(a), org_signals(b)
    if oa and ob and not (oa & ob):
        return -1.0  # hard mismatch — unrelated organizations
    penalty = 0.0
    ya, yb = year_signals(a), year_signals(b)
    if ya and yb and not (ya & yb):
        penalty -= 0.35
    sa, sb = subtype_signals(a), subtype_signals(b)
    if sa and sb and not (sa & sb):
        penalty -= 0.2
    bonus = 0.08 if oa & ob else 0.0
    if ya & yb:
        bonus += 0.05
    return bonus + penalty


def match_score(normalized_a: str, normalized_b: str) -> float:
    """Blend edit-distance ratio with token-set Jaccard (scaled).

    Token overlap dominates for reordered/verbose titles ("UPESSC UP TGT
    Online Form 2026 (17,735 Posts)" vs "UPESSC Assistant Teacher (TGT) 2026
    — 17,735 posts"); SequenceMatcher catches near-identical strings.
    """
    seq = SequenceMatcher(None, normalized_a, normalized_b).ratio()
    set_a, set_b = set(normalized_a.split()), set(normalized_b.split())
    jaccard = len(set_a & set_b) / max(1, len(set_a | set_b))
    return min(1.0, max(seq, jaccard * 1.4))


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
    # Score every (entry, seed) pair, then assign one seed to at most one
    # entry so multiple loose hits on the same curated row cannot inflate
    # coverage. Explicit aliases bypass fuzzy scoring entirely.
    candidates: list[tuple[int, CoverageEntry, str, float, bool, bool]] = []
    for index, entry in enumerate(entries):
        alias_target = _TITLE_ALIASES.get(normalize_title(entry.title)) if kind == "admit_card" else None
        if alias_target:
            # Resolve the normalized alias back to the real seed title so the
            # report names the actual row rather than a normalized string.
            resolved = next(
                (t for t in seed_titles if normalize_title(t) == alias_target),
                alias_target,
            )
            candidates.append((index, entry, resolved, _ALIAS_MATCH_SCORE, True, False))
            continue
        entry_strong = normalize_strong(entry.title)
        best_score, second_score, best_seed = 0.0, 0.0, ""
        for seed_title in seed_titles:
            base = match_score(entry_strong, normalize_strong(seed_title))
            score = max(0.0, base + signal_penalty(entry.title, seed_title))
            if score > best_score:
                second_score, best_score, best_seed = best_score, score, seed_title
            elif score > second_score:
                second_score = score
        close_second = second_score >= threshold - 0.03 and second_score >= best_score - 0.03
        weak_signals = (
            score < threshold + 0.05
            and bool(
                (year_signals(entry.title) and year_signals(best_seed)
                 and not (year_signals(entry.title) & year_signals(best_seed)))
                or (subtype_signals(entry.title) and subtype_signals(best_seed)
                    and not (subtype_signals(entry.title) & subtype_signals(best_seed)))
            )
        ) if best_seed else False
        candidates.append((index, entry, best_seed, best_score, False, close_second or weak_signals))

    # Aliases first, then strongest scores; greedy one-to-one assignment.
    candidates.sort(key=lambda c: (c[4], c[3]), reverse=True)
    used_seeds: set[str] = set()
    used_entries: set[int] = set()
    matched: list[tuple[CoverageEntry, str, float]] = []
    ambiguous: list[tuple[CoverageEntry, str, float]] = []
    duplicate_matches: dict[str, list[str]] = {}
    for index, entry, seed, score, is_alias, is_ambiguous in candidates:
        if not is_alias and score < threshold:
            continue
        if is_ambiguous and not is_alias:
            ambiguous.append((entry, seed, score))
            continue
        if seed in used_seeds:
            duplicate_matches.setdefault(seed, []).append(entry.title)
            continue
        used_seeds.add(seed)
        used_entries.add(index)
        matched.append((entry, seed, score))

    missing = [e for i, e in enumerate(entries) if i not in used_entries]
    return CoverageReport(
        source_url=source_url,
        entries=entries,
        matched=matched,
        missing=missing,
        seed_count=len(seed_titles),
        filtered_out=filtered_out,
        kind=kind,
        distinct_matched_seeds=sorted(used_seeds),
        ambiguous=ambiguous,
        duplicate_matches=duplicate_matches,
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
            f"matched entries (1:1): {len(report.matched)} ({report.coverage_pct}%) | "
            f"distinct seeds: {len(report.distinct_matched_seeds)}/{report.seed_count} "
            f"({report.distinct_seed_pct}%)"
        ),
        (
            f"unmatched: {len(report.missing)} | duplicate candidates: "
            f"{sum(len(v) for v in report.duplicate_matches.values())} | "
            f"ambiguous: {len(report.ambiguous)}"
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
    from app.services.notifier import send_admin_alert

    if not report.missing:
        return True
    text = format_report(report)
    if not settings.TELEGRAM_ADMIN_CHAT_ID:
        logger.info("admin chat not configured; watchdog report not sent (%d gaps)", len(report.missing))
        return False
    return await send_admin_alert(text)


async def coverage_watchdog_loop(interval_seconds: int = _WATCHDOG_INTERVAL_SECONDS) -> None:
    """Weekly watchdog: report coverage gaps and feed unmatched admit-card
    entries into the discovery queue (research only, never publishes)."""
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
                    if kind == "admit_card":
                        # Same watchdog pass: feed unmatched entries to the
                        # discovery queue without re-scraping the aggregator.
                        try:
                            from app.core.database import AsyncSessionLocal
                            from app.services.discovery_engine import run_discovery

                            async with AsyncSessionLocal() as db:
                                await run_discovery(db, report.missing)
                        except Exception:
                            logger.exception("discovery run from watchdog failed")
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
