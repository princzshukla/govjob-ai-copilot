"""Stable, collision-free URL keys for public detail pages.

The key is `<slugified-title>-<normalised full id>`. Using the *whole* id as the
suffix makes lookup exact: two different records can never resolve to the same
URL, and short ids such as ``afcat`` work like any other.
"""

import re


def id_suffix(record_id: str) -> str:
    """Full id, lowercased with '-' and '_' removed.

    This must stay identical to the SQL normalisation in the detail endpoints.
    """
    return record_id.lower().replace("-", "").replace("_", "")


def slug_for(title: str, record_id: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:80].rstrip("-")
    suffix = id_suffix(record_id)
    return f"{base}-{suffix}" if base else suffix


def id_prefix_from_slug(key: str) -> str | None:
    suffix = key.rsplit("-", 1)[-1]
    return suffix or None
