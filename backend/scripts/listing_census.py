"""Exact listing census for sarkariresult.com.cm (read-only).

Counts what the site actually renders, using DOM selectors rather than the
coverage watchdog's loose regexes:

* real listing anchors inside the jobs / admit-card lists;
* ad placeholders (``li.latest-post-ad``) separately, so they are never
  counted as listings;
* relevance-filtered totals (jobs vs non-jobs, admit cards vs date sheets);
* pagination / "load more" links — followed when present.

The result is a JSON dict with exact counts and a ``markup_ok`` flag. It is
used both by the CLI and by the Jobs Watchdog report; the browser MCP is only
a manual cross-check, never a runtime dependency.

Usage (from backend/):
    python scripts/listing_census.py            # human-readable
    python scripts/listing_census.py --json     # machine-readable
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import httpx
from lxml import html as lxml_html
from lxml.etree import ParserError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # allow `python scripts/listing_census.py`

from app.services import coverage_watchdog as cw
from app.services import jobs_watchdog as jw

MAX_PAGES = 10
_JOBS_LIST_CLASS = "latest-posts-last-date"
_ADMIT_LIST_CLASSES = ("wp-block-latest-posts__list", "latest-posts__list")
_AD_TOKENS = ("latest-post-ad", "adsense-between-posts")
_PAGINATION_RE = re.compile(r"/page/\d+|[?&]paged=\d+|load\s*more|next|older", re.I)


def _has_class(token: str):
    """XPath predicate for a whitespace-delimited CSS class token."""
    return f'contains(concat(" ", normalize-space(@class), " "), " {token} ")'


def _clean(text: str | None) -> str:
    return " ".join((text or "").split())


def _next_page_urls(page_html: str, page_url: str) -> list[str]:
    try:
        doc = lxml_html.fromstring(page_html)
    except (ValueError, TypeError, ParserError):
        return []
    urls: list[str] = []
    for anchor in doc.xpath("//a[@href]"):
        href = _clean(anchor.get("href"))
        text = _clean("".join(anchor.itertext()))
        if _PAGINATION_RE.search(href) or _PAGINATION_RE.search(text):
            url = urljoin(page_url, href)
            if url != page_url and url not in urls:
                urls.append(url)
    return urls


def count_page(page_html: str, source_url: str, kind: str) -> dict:
    """Count listings on one rendered page.

    ``kind`` is 'jobs' or 'admit_cards'.
    """
    try:
        doc = lxml_html.fromstring(page_html)
    except (ValueError, TypeError, ParserError):
        doc = None
    if kind == "jobs":
        class_predicate = _has_class(_JOBS_LIST_CLASS)
    else:
        class_predicate = " or ".join(_has_class(c) for c in _ADMIT_LIST_CLASSES)
    xpath = f'//ul[{class_predicate}]'
    lists = doc.xpath(xpath) if doc is not None else []
    selector_found = bool(lists)
    listing_lis = doc.xpath(xpath + '//li[.//a[@href]]') if selector_found else []
    ad_predicate = " or ".join(_has_class(c) for c in _AD_TOKENS)
    ads = doc.xpath(f'//li[{ad_predicate}]') if doc is not None else []

    titles: list[str] = []
    for li in listing_lis:
        anchor = li.xpath('.//a[@href]')[0]
        titles.append(_clean("".join(anchor.itertext())))

    if kind == "jobs":
        kept = [t for t in titles if t and jw.is_job_entry(
            cw.CoverageEntry(title=t, url="", last_date=None)
        )]
    else:
        kept = [t for t in titles if t and not cw._NOT_ADMIT_RE.search(t)]

    return {
        "source_url": source_url,
        "kind": kind,
        "selector_found": selector_found,
        "raw_listings": len(listing_lis),
        "ad_placeholders": len(ads),
        "filtered_out": len(titles) - len(kept),
        "effective_listings": len(kept),
        "titles": titles[:5],  # small evidence sample, never stored verbatim in reports
    }


async def collect_census(
    jobs_html: str | None = None,
    admit_html: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict:
    """Return exact counts for both pages, following pagination when present."""
    pages = {
        "jobs": (jobs_html, cw.LATEST_JOBS_URL),
        "admit_cards": (admit_html, cw.ADMIT_CARD_URL),
    }

    async def _fetch(url: str, client_: httpx.AsyncClient) -> str:
        response = await client_.get(url, timeout=cw.FETCH_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.text

    results: dict[str, dict] = {}
    drift: list[str] = []
    if client is None:
        async with httpx.AsyncClient(
            timeout=cw.FETCH_TIMEOUT_SECONDS, follow_redirects=True,
            headers={"User-Agent": cw.USER_AGENT},
        ) as owned:
            return await collect_census(jobs_html, admit_html, client=owned)

    for kind, (html_text, url) in pages.items():
        seen_urls: set[str] = set()
        aggregate = {
            "source_url": url, "kind": kind, "selector_found": False,
            "raw_listings": 0, "ad_placeholders": 0,
            "filtered_out": 0, "effective_listings": 0, "titles": [],
            "pages_fetched": 0, "pagination_detected": False,
        }
        current_url = url
        current_html = html_text
        for _page_no in range(MAX_PAGES):
            if current_html is None:
                current_html = await _fetch(current_url, client)
            page = count_page(current_html, current_url, kind)
            aggregate["selector_found"] = aggregate["selector_found"] or page["selector_found"]
            for key in ("raw_listings", "ad_placeholders", "filtered_out"):
                aggregate[key] += page[key]
            aggregate["effective_listings"] += page["effective_listings"]
            if len(aggregate["titles"]) < 5:
                aggregate["titles"].extend(page["titles"][:5 - len(aggregate["titles"])])
            aggregate["pages_fetched"] += 1
            seen_urls.add(current_url)
            next_urls = [u for u in _next_page_urls(current_html, current_url) if u not in seen_urls]
            aggregate["pagination_detected"] = aggregate["pagination_detected"] or bool(next_urls)
            if not next_urls:
                break
            current_url, current_html = next_urls[0], None
        results[kind] = aggregate
        if not aggregate["selector_found"] or aggregate["raw_listings"] == 0:
            drift.append(f"{kind}: listing selector missing or zero listings — markup may have changed")

    return {
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "jobs": results["jobs"],
        "admit_cards": results["admit_cards"],
        "markup_ok": not drift,
        "drift": drift,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print JSON")
    args = parser.parse_args()
    result = asyncio.run(collect_census())
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    for kind, label in (("jobs", "Latest Jobs"), ("admit_cards", "Admit Cards")):
        item = result[kind]
        print(
            f"{label}: {item['raw_listings']} listings rendered "
            f"({item['ad_placeholders']} ad placeholders excluded) | "
            f"{item['effective_listings']} relevant | "
            f"{item['filtered_out']} filtered out | "
            f"{item['pages_fetched']} page(s) | "
            f"pagination: {item['pagination_detected']}"
        )
    if result["drift"]:
        print("DRIFT: " + "; ".join(result["drift"]))


if __name__ == "__main__":
    main()
