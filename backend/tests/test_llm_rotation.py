"""Groq multi-key rotation (offline, mocked client)."""
from __future__ import annotations

import pytest

from app.services import notification_extractor as nx


class FakeCompletion:
    def __init__(self, results):
        self.results = results

    async def create(self, **_kwargs):
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FakeChat:
    def __init__(self, results):
        self.completions = FakeCompletion(results)


class FakeClient:
    def __init__(self, result_sequence):
        self.chat = FakeChat(list(result_sequence))


def _response(text):
    return type("R", (), {"choices": [type("C", (), {"message": type("M", (), {"content": text})()})()]})()


class _RateLimited(Exception):
    status_code = 429


def test_rotation_uses_second_key_on_429(monkeypatch):
    monkeypatch.setattr(nx.settings, "GROQ_API_KEY", "key-primary")
    monkeypatch.setattr(nx.settings, "GROQ_API_KEY_EXTRA", "key-secondary")
    monkeypatch.setattr(nx, "_client", None)
    monkeypatch.setattr(nx, "_key_index", 0)

    created = []
    clients = {}

    def fake_groq():
        idx = nx._key_index
        created.append(idx)
        if idx not in clients:
            clients[idx] = FakeClient(
                [_RateLimited("rate limited")] if idx == 0 else [_response('{"ok":true}')]
            )
        return clients[idx]

    monkeypatch.setattr(nx, "_groq", fake_groq)
    monkeypatch.setattr(nx.asyncio, "sleep", lambda _s: None)

    out = __import__("asyncio").run(nx._groq_completion(lambda _b: []))
    assert out == '{"ok":true}'
    assert created == [0, 1]  # rotated to the second key


def test_no_rotation_with_single_key(monkeypatch):
    monkeypatch.setattr(nx.settings, "GROQ_API_KEY", "key-primary")
    monkeypatch.setattr(nx.settings, "GROQ_API_KEY_EXTRA", "")
    assert nx._groq_keys() == ["key-primary"]
    assert nx._rotate_groq_key() is False
