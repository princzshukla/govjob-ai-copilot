"""Telegram delivery — verified user chats and pipeline admin alerts.

Security rules:
* Plain text only (no ``parse_mode``): notification titles are untrusted.
* Secrets (bot token, chat ids) are **never** logged — only ``mask_secret``
  renderings and HTTP status codes.
* ``TELEGRAM_BOT_TOKEN`` and ``TELEGRAM_ADMIN_CHAT_ID`` are validated in
  ``app.core.config`` at load time, so a bot token can never sit in the
  chat-id slot unnoticed again.
* All pipeline code should call ``send_admin_alert`` (single validated path);
  ``send_telegram_alert`` remains for per-user verified chats.
"""
import argparse
import asyncio
import logging

import httpx

from app.core.config import settings, mask_secret, _TELEGRAM_CHAT_RE

from app.core.logging_config import RedactSecretsFilter

for _logger in (logging.getLogger("httpx"), logging.getLogger()):
    _logger.addFilter(RedactSecretsFilter())

logger = logging.getLogger(__name__)


def _valid_chat(chat_id: object) -> bool:
    return isinstance(chat_id, str) and bool(_TELEGRAM_CHAT_RE.match(chat_id.strip()))


async def send_telegram_alert(chat_id: str, message: str) -> bool:
    """Dispatch a plain-text Telegram message via the Bot API.

    Returns False when configuration is invalid; logs contain no secrets.
    """
    token = settings.TELEGRAM_BOT_TOKEN.strip()
    chat = (chat_id or "").strip()

    if not token or not _valid_chat(chat):
        logger.info(
            "Telegram alert skipped: token=%s chat=%s (invalid configuration)",
            "set" if token else "unset",
            "set" if chat else "unset",
        )
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat, "text": message[:4000]}

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(url, json=payload)
        except httpx.HTTPError:
            logger.warning("Telegram request failed (network error)")
            return False

    if resp.status_code != 200:
        logger.warning("Telegram rejected message: HTTP %s (chat %s)", resp.status_code, mask_secret(chat))
        return False
    return True


async def send_admin_alert(message: str) -> bool:
    """Single entry point for all pipeline alerts. No-op when unconfigured."""
    if not settings.TELEGRAM_ADMIN_CHAT_ID:
        logger.info("admin alert skipped: TELEGRAM_ADMIN_CHAT_ID unset | %s", message[:200])
        return False
    ok = await send_telegram_alert(settings.TELEGRAM_ADMIN_CHAT_ID, message)
    if not ok:
        logger.warning("admin alert delivery failed (chat %s)", mask_secret(settings.TELEGRAM_ADMIN_CHAT_ID))
    return ok


async def test_admin_delivery() -> tuple[bool, str]:
    """Validate bot token with getMe, then send a real test message.

    Returns ``(success, log_safe_summary)``. Never prints the token or chat id.
    """
    token = settings.TELEGRAM_BOT_TOKEN.strip()
    chat = settings.TELEGRAM_ADMIN_CHAT_ID.strip()
    if not token or not _valid_chat(chat):
        return False, f"invalid config: token={'set' if token else 'unset'}, chat={'set' if chat else 'unset'}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            me = await client.get(f"https://api.telegram.org/bot{token}/getMe")
        except httpx.HTTPError:
            return False, "getMe failed (network error)"
        if me.status_code != 200 or not me.json().get("ok"):
            return False, f"getMe rejected: HTTP {me.status_code}"
        username = me.json().get("result", {}).get("username", "")
    sent = await send_admin_alert("GovJob Copilot: Telegram admin alert test (safe to ignore).")
    summary = (
        f"bot @{username or 'unnamed'} reachable; "
        f"chat={mask_secret(chat)}; test_message={'delivered' if sent else 'FAILED'}"
    )
    logger.info("telegram test: %s", summary)
    return sent, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Telegram delivery diagnostics")
    parser.add_argument("--test-admin", action="store_true", help="send a real test alert to the admin chat")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.test_admin:
        ok, summary = asyncio.run(test_admin_delivery())
        print(f"{'OK' if ok else 'FAIL'}: {summary}")
        raise SystemExit(0 if ok else 1)
    parser.print_help()


if __name__ == "__main__":
    main()
