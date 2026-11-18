"""Centralized watcher registry — the only list the seeder needs."""
from __future__ import annotations

from .boards import WATCHERS
from .base import BaseWatcher

_BY_SLUG = {w.slug: w for w in WATCHERS}


def all_watchers() -> list[BaseWatcher]:
    """Priority order (1 = critical) then slug for stable scheduling."""
    return sorted(WATCHERS, key=lambda w: (w.priority, w.slug))


def watcher_specs() -> list[dict]:
    return [w.spec() for w in all_watchers()]


def watcher_slugs() -> set[str]:
    return set(_BY_SLUG)


def get(slug: str) -> BaseWatcher | None:
    return _BY_SLUG.get(slug)


def schedule_summary() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {f"priority_{p}": [] for p in (1, 2, 3)}
    for w in all_watchers():
        out[f"priority_{w.priority}"].append(f"{w.slug}:{w.interval_seconds}s")
    return out
