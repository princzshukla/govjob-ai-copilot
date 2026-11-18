"""Board-specific watcher definitions.

URLs are the boards' own public pages (or portals for login-walled boards).
Selectors are intentionally conservative: no selector means Layer 1 hashes the
whole rendered page; a tight link_pattern keeps irrelevant links out. Every
watcher is a ScrapeSource spec consumed by the existing poller — no duplicate
ingestion or storage service.
"""
from __future__ import annotations

from .base import BaseWatcher
from .transports import PlaywrightWatcher, HttpWatcher

_PDF_OR_ADMIT = r"\.pdf($|\?)|admit|hall.?ticket|call.?letter|exam.?city"

WATCHERS: list[BaseWatcher] = [
    # priority 1 — high-volume admit-card publishers, 5 min
    PlaywrightWatcher(
        slug="upsssc-admit-cards", name="UPSSSC — Admit Cards / Notifications",
        url="https://upsssc.gov.in/AllNotifications.aspx", priority=1, interval_seconds=300,
        css_selector="#content_3", link_pattern=r"admitcard|ViewPdf|\.pdf($|\?)",
        extra_config={"organizing_body": "UPSSSC"},
    ),
    PlaywrightWatcher(
        slug="rssb-home", name="RSSB — News / Notices",
        url="https://rssb.rajasthan.gov.in/", priority=1, interval_seconds=300,
        link_pattern=r"/storage/(news_item|admitcard_item|advertisement_item)/[^/]+\.pdf",
        extra_config={"organizing_body": "RSSB (Rajasthan)"},
    ),
    PlaywrightWatcher(
        slug="uppsc-admit-watch", name="UPPSC — Notices / Admit Cards",
        url="https://uppsc.up.nic.in/Default.aspx", priority=1, interval_seconds=900,
        link_pattern=_PDF_OR_ADMIT, extra_config={"organizing_body": "UPPSC"},
    ),
    # priority 2 — national portals, 15 min (login-walled: only public notices)
    PlaywrightWatcher(
        slug="ibps-admit-watch", name="IBPS — Public Notices",
        url="https://www.ibps.in/", priority=2, interval_seconds=900,
        link_pattern=_PDF_OR_ADMIT, extra_config={"organizing_body": "IBPS"},
    ),
    PlaywrightWatcher(
        slug="sbi-admit-watch", name="SBI — Careers / Public Notices",
        url="https://sbi.bank.in/web/careers", priority=2, interval_seconds=900,
        link_pattern=_PDF_OR_ADMIT, extra_config={"organizing_body": "SBI"},
    ),
    PlaywrightWatcher(
        slug="rrb-admit-watch", name="RRB — Public Notices",
        url="https://rrb.indianrailways.gov.in/", priority=2, interval_seconds=900,
        link_pattern=_PDF_OR_ADMIT, extra_config={"organizing_body": "RRB"},
    ),
    PlaywrightWatcher(
        slug="cisf-admit-watch", name="CISF — Public Notices",
        url="https://cisf.gov.in/", priority=2, interval_seconds=900,
        link_pattern=_PDF_OR_ADMIT, extra_config={"organizing_body": "CISF"},
    ),
    PlaywrightWatcher(
        slug="crpf-admit-watch", name="CRPF — Public Notices",
        url="https://crpf.gov.in/", priority=2, interval_seconds=900,
        link_pattern=_PDF_OR_ADMIT, extra_config={"organizing_body": "CRPF"},
    ),
    PlaywrightWatcher(
        slug="bsf-admit-watch", name="BSF — Public Notices",
        url="https://bsf.gov.in/", priority=2, interval_seconds=900,
        link_pattern=_PDF_OR_ADMIT, extra_config={"organizing_body": "BSF"},
    ),
]
