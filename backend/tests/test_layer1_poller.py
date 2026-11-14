"""Deterministic unit tests for the Layer 1 poller — no network, no DB."""
from __future__ import annotations

import re

import pytest

from app.services import layer1_poller as lp


def test_normalize_strips_volatile_noise():
    html = """
    <html><head><meta charset="utf-8"><style>body{color:red}</style></head>
    <body><script nonce="ABC123">var x=1</script>
    <div id="content" data-view-dom-id="view-dom-id-aa11bb22cc33">
    <div class="view view-what-new view-dom-id-0123456789abcdef01234567">Notification</div>
    <img src="data:image/png;base64,AAAABBBBCCCCDDDDEEEEFFFFGGGGHHHHIIIIJJJJKKKKLLLLMMMMNNNNOOOOPPPPQQQQRRRRSSSSTTTTUUUUVVVVWWWWWXXXXYYYYZZZZ">
    </div></body></html>
    """
    out = lp.normalize_content(html)
    assert "script" not in out.lower()
    assert "<style" not in out.lower()
    assert "ABC123" not in out
    assert "view-dom-id-aa11bb22cc33" not in out
    assert "view-dom-id-0123456789abcdef01234567" not in out
    assert "image/png;base64" not in out
    assert "Notification" in out


def test_normalize_is_stable_across_renders():
    def page(token: str) -> str:
        return f"""
        <div class="view view-x view-dom-id-{token}"><ul><li><a href="/x.pdf">Link</a></li></ul></div>
        """

    a = lp.normalize_content(page("aa11bb22cc33"))
    b = lp.normalize_content(page("ff00ee11dd22"))
    assert a == b


def test_extract_dedup_key_variants():
    assert lp.extract_dedup_key("Advertisement No. 13-2026 — Dental Surgeon") == "13-2026"
    assert lp.extract_dedup_key("Advt No. 11/2026") == "11-2026"
    assert lp.extract_dedup_key("Notification No: 2/2027") == "2-2027"
    assert lp.extract_dedup_key(None, "https://x.gov.in/sites/default/files/AdvtNo-5-2026-Engl.pdf") == "5-2026"
    assert lp.extract_dedup_key("Just some plain text with year 2026 and no number") is None
    assert lp.extract_dedup_key("Advertisement No. 9999-2026") is None  # not a plausible ad number


def test_extract_dedup_key_ignores_nonsense_years():
    assert lp.extract_dedup_key("12-1899") is None
    assert lp.extract_dedup_key("12-2026") == "12-2026"


async def test_robots_fail_open_when_robots_unreachable(monkeypatch):
    class _Boom:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            raise httpx_error()

        async def __aexit__(self, *args):
            return False

    def httpx_error():
        import httpx

        return httpx.ConnectError("boom")

    monkeypatch.setattr(lp.httpx, "AsyncClient", _Boom)
    lp._ROBOTS_CACHE.clear()
    assert await lp._robots_allows("https://www.example.gov.in/notices") is True


async def test_robots_allows_when_no_robots_file(monkeypatch):
    class _Resp:
        status_code = 404
        text = ""

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, *args, **kwargs):
            return _Resp()

    monkeypatch.setattr(lp.httpx, "AsyncClient", _Client)
    lp._ROBOTS_CACHE.clear()
    assert await lp._robots_allows("https://www.example.gov.in/notices") is True


async def test_robots_disallows_and_caches(monkeypatch):
    class _Resp:
        status_code = 200
        text = "User-agent: *\nDisallow: /private/\n"

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def get(self, *args, **kwargs):
            return _Resp()

    monkeypatch.setattr(lp.httpx, "AsyncClient", _Client)
    lp._ROBOTS_CACHE.clear()
    assert await lp._robots_allows("https://www.example.gov.in/private/notices") is False
    assert await lp._robots_allows("https://www.example.gov.in/public/notices") is True


def test_poll_outcome_json_serializable():
    outcome = lp.PollOutcome(slug="x", ok=True, new_urls=["https://a.gov.in/x.pdf"])
    import json

    json.dumps(outcome.__dict__)
