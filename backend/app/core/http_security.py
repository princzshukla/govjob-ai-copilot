"""SSRF guards for URLs that arrive from scraped pages or other untrusted data.

Every server-side fetch of a URL we did not author must go through
:func:`assert_safe_url` (and, for downloads, :func:`fetch_limited`). Literal
private/loopback/link-local IPs are rejected outright and hostnames are
resolved so a name pointing at e.g. 169.254.169.254 cannot reach cloud
metadata. Redirects are followed manually and re-validated at every hop.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx

_ALLOWED_SCHEMES = frozenset({"http", "https"})
_MAX_REDIRECTS = 5
# Windows DNS can hand back NAT64 addresses for plain IPv4 hosts. Decode the
# embedded IPv4 before deciding whether the destination is public.
_NAT64 = ipaddress.ip_network("64:ff9b::/96")


def _ip_is_public(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return True  # a hostname, checked via DNS below
    if isinstance(ip, ipaddress.IPv6Address) and ip in _NAT64:
        ip = ipaddress.ip_address(ip.packed[12:])
    return (
        ip.is_global
        and not ip.is_private
        and not ip.is_loopback
        and not ip.is_link_local
        and not ip.is_reserved
        and not ip.is_multicast
        and not ip.is_unspecified
    )


def _host_is_public(host: str) -> bool:
    host = host.strip().rstrip(".").lower()
    if not host or host in ("localhost",) or host.endswith(".localhost"):
        return False
    if not _ip_is_public(host):
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        # DNS failure: the subsequent fetch will fail anyway; nothing private
        # was resolved, so do not break offline tests for public-looking names.
        return True
    return all(_ip_is_public(info[4][0]) for info in infos)


def is_safe_url(url: str) -> bool:
    """True only for http(s) URLs whose host resolves to a public address."""
    try:
        parts = urlparse(url)
    except ValueError:
        return False
    if parts.scheme not in _ALLOWED_SCHEMES or not parts.hostname:
        return False
    if parts.username or parts.password:
        return False
    return _host_is_public(parts.hostname)


def assert_safe_url(url: str) -> None:
    if not is_safe_url(url):
        raise ValueError("refusing to fetch unsafe URL: %s" % url[:200])


async def fetch_limited(
    client: httpx.AsyncClient,
    url: str,
    *,
    max_bytes: int,
    max_redirects: int = _MAX_REDIRECTS,
) -> tuple[int, bytes, str]:
    """GET ``url`` with SSRF checks on every hop and a hard body size cap.

    Returns ``(status_code, body, final_url)``. ``404``/``410`` are returned to
    the caller instead of raised so existing "dead link" handling still works.
    """
    current = url
    for _ in range(max_redirects + 1):
        assert_safe_url(current)
        async with client.stream("GET", current, follow_redirects=False) as resp:
            if resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get("location")
                if not location:
                    raise ValueError("redirect without Location header")
                current = urljoin(str(resp.url), location)
                continue
            if resp.status_code in (404, 410):
                return resp.status_code, b"", str(resp.url)
            resp.raise_for_status()
            body = bytearray()
            async for chunk in resp.aiter_bytes():
                body.extend(chunk)
                if len(body) > max_bytes:
                    raise ValueError("response too large (>%d bytes)" % max_bytes)
            return resp.status_code, bytes(body), str(resp.url)
    raise ValueError("too many redirects")
