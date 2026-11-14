"""Layer 1 (Discovery) scraper worker.

Polls the sources registered in ``scrape_sources`` and keeps three things
consistent:

* ``scrape_logs`` — every run is logged, including no-change runs. The
  48-hour stability test reads ``changed`` from here; ``note`` carries
  ``not-modified(304)`` and other annotations.
* ``raw_discovered_links`` — only links that are NOT already present for the
  source are inserted (dedup on the unique ``(source_id, url)`` index).
  ``published_at`` (when the source exposes it, e.g. SSC notices) times the
  publish→listing-lag metric; ``dedup_key`` (advertisement number) deduplicates
  the same job across sources.
* ``scrape_sources`` — carries ``last_hash`` and the failure bookkeeping
  (``consecutive_failures`` + ``backoff_until``, exponential backoff capped
  at one hour). A failing source never blocks the rest of the batch: each
  source is polled and committed independently.

Good-citizen rules
------------------
* Conditional GETs (ETag / Last-Modified) — a 304 costs one header exchange
  instead of a full page crawl, so a healthy tier-1 source polled every 2
  minutes doesn't hammer a government server.
* robots.txt is honoured per origin (fail-open when it cannot be fetched,
  closed when it explicitly disallows us) — a source disallowed by robots
  gets DISABLED and the admin is alerted, never retried politely forever.
* Zero-link and failure streaks alert a Telegram admin chat instead of
  failing silently (see ``consecutive_zero_runs`` and the failure threshold).

Fetch modes
-----------
* ``httpx``     plain GET + BeautifulSoup. Scoping is done with
                ``css_selector`` so visitor counters / clocks outside the
                notices block cannot flap the hash. ``ignore_selector``
                additionally removes volatile nodes inside the scope.
* ``playwright`` same as httpx but the DOM is rendered first (for JS sites).
                Requires the optional ``playwright`` dependency.
* ``json_api``  for JS frontends backed by a JSON endpoint (ssc.gov.in).
                ``config`` holds ``params``, ``items_path``, ``id_field``,
                ``date_field``, ``attachments_field``, ``title_field`` and a
                ``file_url_template``. The hash is computed over the ordered
                ``(id, createdAt)`` list, so page refreshes cannot change it.

CLI
---
    python -m app.services.layer1_poller --once            # poll every due source once
    python -m app.services.layer1_poller --source local-test-notices
    python -m app.services.layer1_poller --loop            # continuous worker
    python -m app.services.layer1_poller --force           # ignore schedule (harnesses)
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import re
import time
import urllib.parse
import urllib.robotparser
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Comment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.pipeline import RawDiscoveredLink, ScrapeLog, ScrapeSource
from app.services.notifier import send_telegram_alert

logger = logging.getLogger("app.layer1")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 govjob-matcher/1.0"
)
FETCH_TIMEOUT_SECONDS = 25.0
PLAYWRIGHT_TIMEOUT_MS = 45_000
BACKOFF_BASE_SECONDS = 30
BACKOFF_CAP_SECONDS = 3600
LOOP_TICK_SECONDS = 15
FAILURE_ALERT_THRESHOLD = 3
ZERO_LINKS_ALERT_THRESHOLD = 5

# Rendered-per-request attributes that are not content.
_VOLATILE_PATTERNS = [
    (re.compile(r"view-dom-id-[0-9a-f]+", re.I), "view-dom-id-VOLATILE"),
    (re.compile(r"\bdom-id-[0-9a-f]+\b", re.I), "dom-id-VOLATILE"),
    # Embedded session assets (captcha images, encrypted payloads) — rotate
    # every render on NIC portals.
    (re.compile(r"(src|href)=\"data:[^\"]{80,}\""), r'\1="data:VOLATILE"'),
]
_BUILTIN_STRIP_SELECTORS = "script, style, noscript, input, meta, template"
_AD_NUMBER_RE = re.compile(
    r"(?:advt?\.?\s*(?:no\.?|number)?\.?|notification\s*(?:no\.?|number)?\.?|no\.?)?\s*"
    r"(\d{1,4})\s*[-/–.]\s*(20\d{2})",
    re.I,
)


class ScrapeError(Exception):
    """Expected, per-source failure (network, HTTP status, missing selector…)."""


class NotModified(Exception):
    """Source served HTTP 304 (ETag / If-Modified-Since): nothing to do."""


@dataclass
class PollOutcome:
    slug: str
    ok: bool
    changed: bool = False
    links_found: int = 0
    new_links: int = 0
    content_hash: str | None = None
    error: str | None = None
    note: str | None = None
    duration_ms: int = 0
    new_urls: list[str] = field(default_factory=list)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# robots.txt (fail-open when unreadable; hard-stop when explicitly disallowed)
# ---------------------------------------------------------------------------

_ROBOTS_CACHE: dict[str, tuple[float, object]] = {}


async def _robots_allows(url: str) -> bool:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    cached = _ROBOTS_CACHE.get(origin)
    if cached and time.time() - cached[0] < 3600:
        rp = cached[1]
        return True if rp is None else bool(rp.can_fetch(f"*", url))
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.get(origin + "/robots.txt", headers={"User-Agent": USER_AGENT})
        if resp.status_code == 404:
            _ROBOTS_CACHE[origin] = (time.time(), None)
            return True
        if resp.status_code >= 400:
            _ROBOTS_CACHE[origin] = (time.time(), None)
            return True  # unreadable ≠ disallowed
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(resp.text.splitlines())
        _ROBOTS_CACHE[origin] = (time.time(), rp)
        return bool(rp.can_fetch("*", url))
    except Exception:
        _ROBOTS_CACHE[origin] = (time.time(), None)
        return True


# ---------------------------------------------------------------------------
# Content normalization & hashing
# ---------------------------------------------------------------------------

def normalize_content(content: str, ignore_selector: str | None = None) -> str:
    """Return a stable string suitable for hashing."""
    soup = BeautifulSoup(content, "lxml")
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for tag in soup.select(_BUILTIN_STRIP_SELECTORS):
        tag.extract()
    # CSP nonces rotate on every render (BHEL, NIC portals).
    for tag in soup.find_all(True):
        tag.attrs.pop("nonce", None)
    if ignore_selector:
        for tag in soup.select(ignore_selector):
            tag.extract()
    collapsed = re.sub(r"\s+", " ", str(soup)).strip()
    for pattern, replacement in _VOLATILE_PATTERNS:
        collapsed = pattern.sub(replacement, collapsed)
    return collapsed


def compute_hash(normalized: str) -> str:
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _scope_soup(soup: BeautifulSoup, css_selector: str | None) -> BeautifulSoup:
    if not css_selector:
        return soup
    scoped = soup.select_one(css_selector)
    if scoped is None:
        raise ScrapeError(f"css_selector {css_selector!r} matched nothing on the page")
    return scoped


def extract_links(scoped: BeautifulSoup, base_url: str, link_pattern: str | None) -> list[tuple[str, str]]:
    """(url, title) pairs, deduped, http(s) only, fragments stripped."""
    pattern = re.compile(link_pattern, re.I) if link_pattern else None
    seen: set[str] = set()
    links: list[tuple[str, str]] = []
    for anchor in scoped.select("a[href]"):
        raw = (anchor.get("href") or "").strip()
        if not raw or raw.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        absolute = urljoin(base_url, raw)
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https"):
            continue
        url = parsed._replace(fragment="").geturl()
        if url in seen:
            continue
        if url == base_url or url == base_url.rstrip("/"):
            continue
        if pattern and not pattern.search(url):
            continue
        seen.add(url)
        title = anchor.get_text(" ", strip=True)[:300]
        links.append((url, title))
    return links


def extract_dedup_key(title: str | None, url: str | None = None) -> str | None:
    """Best-effort advertisement/notification number, e.g. '13-2026'.

    Same job announced in the Gazette and on two portals gets the same key,
    which is what cross-source dedup needs.
    """
    for text in (title or "", urllib.parse.unquote(url or "")):
        match = _AD_NUMBER_RE.search(text)
        if match:
            number, year = match.group(1), match.group(2)
            try:
                number_int = int(number)
            except ValueError:
                continue
            if 1 <= number_int <= 2000:
                return f"{number_int}-20{year[-2:]}" if not year.startswith("20") else f"{number_int}-{year}"
    return None


# ---------------------------------------------------------------------------
# Fetch modes
# ---------------------------------------------------------------------------

async def _fetch_html_httpx(source: ScrapeSource) -> tuple[str, httpx.Headers]:
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    if source.etag:
        headers["If-None-Match"] = source.etag
    if source.last_modified:
        headers["If-Modified-Since"] = source.last_modified
    async with httpx.AsyncClient(
        timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=True, headers=headers
    ) as client:
        resp = await client.get(source.url)
        if resp.status_code == 304:
            raise NotModified()
        resp.raise_for_status()
        return resp.text, resp.headers


async def _fetch_html_playwright(source: ScrapeSource) -> tuple[str, httpx.Headers]:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise ScrapeError(
            "fetch_mode=playwright requires the optional 'playwright' package "
            "(pip install playwright && playwright install chromium)"
        ) from exc

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            page = await browser.new_page(user_agent=USER_AGENT)
            try:
                await page.goto(source.url, wait_until="networkidle", timeout=PLAYWRIGHT_TIMEOUT_MS)
            except Exception:
                await page.goto(source.url, wait_until="domcontentloaded", timeout=PLAYWRIGHT_TIMEOUT_MS)
            return await page.content(), httpx.Headers()
        finally:
            await browser.close()


async def _fetch_json_api(source: ScrapeSource) -> tuple[str, list[tuple[str, str]], dict[str, datetime]]:
    """Returns (fingerprint, links, published_map).

    The fingerprint covers identity+ordering only; page refreshes cannot
    change it. ``published_map`` carries the source's own publish timestamp
    per link (powers the publish→listing-lag metric).
    """
    cfg = dict(source.config or {})
    params = cfg.get("params") or {}
    async with httpx.AsyncClient(
        timeout=FETCH_TIMEOUT_SECONDS,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    ) as client:
        resp = await client.get(source.url, params=params)
        resp.raise_for_status()
        payload = resp.json()

    items: object = payload
    for key in str(cfg.get("items_path", "data")).split("."):
        if not isinstance(items, dict):
            raise ScrapeError(f"items_path broke at {key!r}: expected object")
        items = items[key]
    if not isinstance(items, list):
        raise ScrapeError("items_path did not resolve to a list")

    id_field = cfg.get("id_field", "id")
    date_field = cfg.get("date_field", "createdAt")
    fingerprint = json.dumps(
        [[item.get(id_field), item.get(date_field)] for item in items],
        separators=(",", ":"),
    )

    title_field = cfg.get("title_field", "headline")
    attachments_field = cfg.get("attachments_field", "attachments")
    template = cfg.get("file_url_template")
    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    published: dict[str, datetime] = {}
    if template:
        for item in items:
            title = str(item.get(title_field) or "")[:300]
            published_at = _parse_iso(item.get(date_field))
            for att in item.get(attachments_field) or []:
                file_name = att.get("fileName") or att.get("filename")
                if not file_name:
                    continue
                merged = {
                    **{k: v for k, v in item.items() if k != "attachments"},
                    **att,
                    "fileName": quote(str(file_name)),
                }
                try:
                    url = template.format(**merged)
                except KeyError as exc:
                    raise ScrapeError(f"file_url_template missing key {exc}") from exc
                if url in seen:
                    continue
                seen.add(url)
                links.append((url, title))
                if published_at is not None:
                    published[url] = published_at
    return fingerprint, links, published


def _parse_iso(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


async def fetch_content(
    source: ScrapeSource,
) -> tuple[str, list[tuple[str, str]], dict[str, datetime], dict[str, str | None]]:
    """Returns (normalized fingerprint, links, published_map, cache_headers)."""
    if source.fetch_mode == "json_api":
        fingerprint, links, published = await _fetch_json_api(source)
        return fingerprint, links, published, {}

    if source.fetch_mode == "playwright":
        html, headers = await _fetch_html_playwright(source)
    elif source.fetch_mode == "httpx":
        html, headers = await _fetch_html_httpx(source)
    else:
        raise ScrapeError(f"unknown fetch_mode {source.fetch_mode!r}")

    soup = BeautifulSoup(html, "lxml")
    scoped = _scope_soup(soup, source.css_selector)
    fingerprint = normalize_content(str(scoped), source.ignore_selector)
    links = extract_links(scoped, source.url, source.link_pattern)
    cache = {
        "etag": headers.get("etag"),
        "last_modified": headers.get("last-modified"),
    }
    return fingerprint, links, {}, cache


# ---------------------------------------------------------------------------
# Polling & persistence
# ---------------------------------------------------------------------------

async def _insert_new_links(
    db: AsyncSession,
    source_id: int,
    links: list[tuple[str, str]],
    published: dict[str, datetime],
) -> list[str]:
    if not links:
        return []
    urls = [url for url, _ in links]
    existing = set(
        (await db.execute(
            select(RawDiscoveredLink.url).where(
                RawDiscoveredLink.source_id == source_id,
                RawDiscoveredLink.url.in_(urls),
            )
        )).scalars().all()
    )
    new_urls: list[str] = []
    for url, title in links:
        if url in existing:
            continue
        db.add(
            RawDiscoveredLink(
                source_id=source_id,
                url=url,
                title=title or None,
                published_at=published.get(url),
                dedup_key=extract_dedup_key(title, url),
            )
        )
        new_urls.append(url)
    return new_urls


def _backoff_seconds(consecutive_failures: int) -> int:
    exponent = min(max(consecutive_failures - 1, 0), 6)
    return min(BACKOFF_CAP_SECONDS, BACKOFF_BASE_SECONDS * (2**exponent))


async def _alert(text: str) -> None:
    if settings.TELEGRAM_ADMIN_CHAT_ID:
        await send_telegram_alert(settings.TELEGRAM_ADMIN_CHAT_ID, text)
    else:
        logger.info("admin alert (no TELEGRAM_ADMIN_CHAT_ID): %s", text)


async def poll_source(db: AsyncSession, source: ScrapeSource) -> PollOutcome:
    started = time.perf_counter()
    now = utcnow()
    outcome = PollOutcome(slug=source.slug, ok=False)

    # robots.txt — a hard-stop is the only compliant reading of "respect it".
    if not await _robots_allows(source.url):
        source.enabled = False
        source.last_checked_at = now
        source.last_error = "robots.txt disallows fetching this path; source disabled"
        outcome.error = source.last_error
        outcome.note = "robots-disallowed"
        logger.warning("source %s disabled: robots.txt disallows it", source.slug)
        await _alert(f"⛔ Layer1 source disabled (robots.txt): {source.slug} — {source.url}")
        db.add(
            ScrapeLog(
                source_id=source.id,
                duration_ms=int((time.perf_counter() - started) * 1000),
                ok=False,
                changed=False,
                note=outcome.note,
                error=outcome.error,
            )
        )
        return outcome

    try:
        fingerprint, links, published, cache = await fetch_content(source)
        content_hash = compute_hash(fingerprint)
        changed = content_hash != source.last_hash

        outcome.content_hash = content_hash
        outcome.changed = changed
        outcome.ok = True
        if changed:
            outcome.links_found = len(links)
            outcome.new_urls = await _insert_new_links(db, source.id, links, published)
            outcome.new_links = len(outcome.new_urls)

        source.last_hash = content_hash
        source.last_checked_at = now
        source.last_success_at = now
        source.consecutive_failures = 0
        source.backoff_until = None
        source.last_error = None
        if cache:
            source.etag = cache.get("etag") or source.etag
            source.last_modified = cache.get("last_modified") or source.last_modified

        # Zero-link health alarm: N clean-but-empty polls in a row means the
        # page layout probably changed and our selector is now garbage.
        if outcome.links_found == 0 and not changed:
            source.consecutive_zero_runs += 1
        elif outcome.links_found > 0:
            source.consecutive_zero_runs = 0
        if source.consecutive_zero_runs == ZERO_LINKS_ALERT_THRESHOLD:
            logger.warning("source %s: zero links for %d consecutive runs", source.slug, source.consecutive_zero_runs)
            await _alert(
                f"⚠️ Layer1 source {source.slug}: 0 links for {source.consecutive_zero_runs} consecutive runs — "
                f"css_selector may no longer match ({source.url})"
            )
    except NotModified:
        outcome.ok = True
        outcome.changed = False
        outcome.note = "not-modified(304)"
        source.last_checked_at = now
        source.last_success_at = now
        source.consecutive_failures = 0
        source.backoff_until = None
        source.last_error = None
    except Exception as exc:  # network, HTTP, parse, selector — all per-source
        logger.warning("poll failed for %s: %s", source.slug, exc)
        source.last_checked_at = now
        source.consecutive_failures += 1
        source.backoff_until = now + timedelta(seconds=_backoff_seconds(source.consecutive_failures))
        source.last_error = f"{type(exc).__name__}: {exc}"[:2000]
        outcome.error = source.last_error
        if source.consecutive_failures == FAILURE_ALERT_THRESHOLD:
            await _alert(
                f"⚠️ Layer1 source {source.slug}: {source.consecutive_failures} consecutive failures — {exc}"
            )

    outcome.duration_ms = int((time.perf_counter() - started) * 1000)
    db.add(
        ScrapeLog(
            source_id=source.id,
            duration_ms=outcome.duration_ms,
            ok=outcome.ok,
            changed=outcome.changed,
            links_found=outcome.links_found,
            new_links=outcome.new_links,
            content_hash=outcome.content_hash,
            error=outcome.error,
            note=outcome.note,
        )
    )
    return outcome


def _due(source: ScrapeSource, now: datetime) -> bool:
    if source.backoff_until is not None and source.backoff_until > now:
        return False
    if source.last_checked_at is None:
        return True
    return (now - source.last_checked_at).total_seconds() >= source.interval_seconds


async def run_once(
    only_slug: str | None = None,
    ignore_schedule: bool = False,
    force: bool = False,
) -> list[PollOutcome]:
    """Poll due sources once each. One source's failure never affects the next."""
    outcomes: list[PollOutcome] = []
    async with AsyncSessionLocal() as db:
        query = select(ScrapeSource).where(ScrapeSource.enabled.is_(True)).order_by(ScrapeSource.tier, ScrapeSource.id)
        if only_slug:
            query = select(ScrapeSource).where(ScrapeSource.slug == only_slug)
        sources = list((await db.execute(query)).scalars().all())
        now = utcnow()
        for source in sources:
            if not force and not ignore_schedule and not only_slug and not _due(source, now):
                logger.debug("skipping %s (not due / backing off)", source.slug)
                continue
            try:
                outcome = await poll_source(db, source)
                # Commit per source so a bad commit cannot poison the batch.
                await db.commit()
                outcomes.append(outcome)
            except Exception:
                await db.rollback()
                logger.exception("source %s blew up outside the guarded path", source.slug)
                outcomes.append(PollOutcome(slug=source.slug, ok=False, error="internal error"))
    return outcomes


async def run_loop() -> None:
    logger.info("layer1 poller loop started (tick=%ss)", LOOP_TICK_SECONDS)
    while True:
        try:
            outcomes = await run_once()
            for outcome in outcomes:
                logger.info(
                    "poll %s ok=%s changed=%s new_links=%d (%dms)",
                    outcome.slug, outcome.ok, outcome.changed, outcome.new_links, outcome.duration_ms,
                )
        except Exception:
            logger.exception("poller tick failed")
        await asyncio.sleep(LOOP_TICK_SECONDS)


def main() -> None:
    parser = argparse.ArgumentParser(description="Layer 1 discovery poller")
    parser.add_argument("--once", action="store_true", help="poll every due source once and exit")
    parser.add_argument("--loop", action="store_true", help="run the continuous worker loop")
    parser.add_argument("--source", metavar="SLUG", help="poll one source, ignoring schedule")
    parser.add_argument("--force", action="store_true", help="poll every enabled source, ignoring schedule and backoff")
    parser.add_argument("--json", action="store_true", help="print outcomes as JSON")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.loop:
        asyncio.run(run_loop())
        return
    outcomes = asyncio.run(run_once(only_slug=args.source, ignore_schedule=bool(args.source), force=args.force))
    if args.json:
        print(json.dumps([o.__dict__ for o in outcomes], indent=2, default=str))
    else:
        for o in outcomes:
            status = "OK " if o.ok else "ERR"
            line = f"[{status}] {o.slug:28s} changed={o.changed} links_found={o.links_found} new={o.new_links} {o.duration_ms}ms"
            if o.note:
                line += f" note={o.note}"
            if o.error:
                line += f" error={o.error}"
            print(line)


if __name__ == "__main__":
    main()
