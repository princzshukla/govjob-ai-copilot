"""HTTP and Playwright watcher variants (both feed Layer 1 unchanged)."""
from __future__ import annotations

from .base import BaseWatcher


class HttpWatcher(BaseWatcher):
    fetch_mode: str = "httpx"


class PlaywrightWatcher(BaseWatcher):
    fetch_mode: str = "playwright"
