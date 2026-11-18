"""Base watcher abstraction.

Watchers never ingest anything themselves: they only declare a ScrapeSource
spec that the existing Layer-1 poller consumes (hash gate, robots, retries,
dedup, scrape_logs). This keeps one ingestion path and one database model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BaseWatcher:
    slug: str
    name: str
    url: str
    priority: int = 2                 # 1 = critical (2-5 min), 2 = normal (15 min), 3 = slow
    interval_seconds: int = 900
    fetch_mode: str = "httpx"
    css_selector: str | None = None
    ignore_selector: str | None = None
    link_pattern: str | None = None
    notice_kind: str | None = None
    extra_config: dict[str, Any] = field(default_factory=dict)

    def spec(self) -> dict[str, Any]:
        config: dict[str, Any] = dict(self.extra_config)
        if self.notice_kind:
            config["notice_kind"] = self.notice_kind
        return {
            "slug": self.slug,
            "name": self.name,
            "url": self.url,
            "tier": self.priority,
            "fetch_mode": self.fetch_mode,
            "css_selector": self.css_selector,
            "ignore_selector": self.ignore_selector,
            "link_pattern": self.link_pattern,
            "interval_seconds": self.interval_seconds,
            "config": config,
        }
