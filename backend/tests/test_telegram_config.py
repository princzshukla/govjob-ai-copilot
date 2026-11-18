"""Telegram configuration & secret hygiene (no network)."""
from __future__ import annotations

import logging

import pytest

from app.core.config import (
    Settings,
    mask_secret,
    _TELEGRAM_CHAT_RE,
    _TELEGRAM_TOKEN_RE,
)
from app.services import notifier


def test_token_and_chat_patterns():
    token = "123456789:AAabcdefghijklmnopqrstuvwxyz0123456789"
    assert _TELEGRAM_TOKEN_RE.match(token)
    assert not _TELEGRAM_TOKEN_RE.match("123456789")
    assert _TELEGRAM_CHAT_RE.match("1234567890")
    assert _TELEGRAM_CHAT_RE.match("@my_channel")
    assert not _TELEGRAM_CHAT_RE.match(token)  # a token is NEVER a chat id


def test_validators_reject_swapped_values(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "123456789:AAabcdefghijklmnopqrstuvwxyz0123456789")
    with pytest.raises(Exception):
        Settings(_env_file=None)  # type: ignore[call-arg]

    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "1234567890")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456")
    with pytest.raises(Exception):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_mask_never_returns_full_secret():
    token = "123456789:AAabcdefghijklmnopqrstuvwxyz0123456789"
    masked = mask_secret(token, keep=4)
    assert token not in masked
    assert masked.startswith("***")
    assert mask_secret("") == "<unset>"


async def test_alert_skipped_with_invalid_chat_and_never_logs_secret(monkeypatch, caplog):
    monkeypatch.setattr(notifier.settings, "TELEGRAM_BOT_TOKEN", "123456789:AAabcdefghijklmnopqrstuvwxyz0123456789")
    monkeypatch.setattr(notifier.settings, "TELEGRAM_ADMIN_CHAT_ID", "not-a-chat")
    caplog.set_level(logging.INFO)
    result = await notifier.send_telegram_alert("not-a-chat", "hello")
    assert result is False
    text = caplog.text
    assert "123456789:AAabc" not in text
    assert "not-a-chat" not in text
