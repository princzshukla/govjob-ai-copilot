"""Reusable admit-card watchers.

All watchers produce ScrapeSource specs for the existing Layer-1 poller.
Nothing here downloads, extracts or writes to the database directly.
"""
from .base import BaseWatcher
from .transports import HttpWatcher, PlaywrightWatcher
from .registry import all_watchers, get, schedule_summary, watcher_slugs, watcher_specs

__all__ = [
    "BaseWatcher", "HttpWatcher", "PlaywrightWatcher",
    "all_watchers", "get", "schedule_summary", "watcher_slugs", "watcher_specs",
]
