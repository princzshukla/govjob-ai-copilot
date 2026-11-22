"""Rate-limit key must come from the edge-set IP, not a varying proxy hop."""

from app.core.rate_limit import client_key


class _Client:
    host = "10.9.9.9"


class _Request:
    def __init__(self, headers: dict[str, str]):
        self.headers = headers
        self.client = _Client()


def test_edge_client_ip_is_used_when_marker_present():
    request = _Request({"cf-ray": "abc", "cf-connecting-ip": "1.2.3.4"})
    assert client_key(request) == "1.2.3.4"


def test_vercel_forwarded_ip_is_used_when_marker_present():
    request = _Request({"x-vercel-id": "abc", "x-vercel-forwarded-for": "5.6.7.8"})
    assert client_key(request) == "5.6.7.8"


def test_no_edge_marker_falls_back_to_connection():
    request = _Request({"cf-connecting-ip": "1.2.3.4"})
    assert client_key(request) == "10.9.9.9"


def test_invalid_edge_ip_is_ignored():
    request = _Request({"cf-ray": "abc", "cf-connecting-ip": "not-an-ip"})
    assert client_key(request) == "10.9.9.9"
