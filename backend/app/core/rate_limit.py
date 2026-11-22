"""Rate-limit key resolution.

The production path is visitor -> Cloudflare -> Vercel -> Render -> uvicorn.
With ``--forwarded-allow-ips=*`` uvicorn takes the leftmost X-Forwarded-For
entry, which on that path changes per request. That gives every request its own
bucket, so the limits never fire.

Cloudflare and Vercel both set an explicit, edge-owned client-IP header and an
edge marker header. Those are used first; the connection address is only a
fallback for direct-to-Render traffic.
"""

import ipaddress

from slowapi import Limiter

from app.core.config import settings


def _clean_ip(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.strip().split(",")[0].strip()
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        return None
    return candidate


def client_key(request) -> str:
    """Stable client identity for rate limiting."""
    headers = request.headers
    edge_marker = "cf-ray" in headers or "x-vercel-id" in headers
    if edge_marker:
        for name in ("cf-connecting-ip", "x-vercel-forwarded-for", "true-client-ip"):
            ip = _clean_ip(headers.get(name))
            if ip:
                return ip
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


# headers_enabled is intentionally off: slowapi requires every limited endpoint
# to declare a `Response` parameter when it is on, and most of ours do not.
# The X-Debug-IP response header in main.py provides the diagnostics instead.
limiter = Limiter(
    key_func=client_key,
    storage_uri=settings.RATE_LIMIT_STORAGE_URL,
)
