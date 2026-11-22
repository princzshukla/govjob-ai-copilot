"""Stable, human-readable URL keys for public detail pages.

The key is `<slugified-title>-<first 8 chars of id>`. The id suffix keeps it
globally unique and lets the API find the row without a database migration.
The title part is decoration: if a title is corrected later, old links keep
working because lookup uses only the id prefix.
"""

import re


def id_suffix(record_id: str) -> str:
    """First 8 alphanumeric characters - never starts or ends with a hyphen."""
    return re.sub(r"[^a-z0-9]", "", record_id.lower())[:8]


def slug_for(title: str, record_id: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:80].rstrip("-")
    suffix = id_suffix(record_id)
    return f"{base}-{suffix}" if base else suffix


def id_prefix_from_slug(key: str) -> str | None:
    prefix = key.rsplit("-", 1)[-1]
    return prefix if len(prefix) >= 6 else None
