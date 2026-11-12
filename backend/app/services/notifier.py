import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_telegram_alert(chat_id: str, message: str) -> bool:
    """Dispatch a plain-text Telegram message via the Bot API.

    Plain text (no ``parse_mode``) is deliberate: exam titles are untrusted
    input, and Markdown would let them break or inject formatting. Falls back
    to a log line when TELEGRAM_BOT_TOKEN is not configured.
    """
    token = settings.TELEGRAM_BOT_TOKEN

    if not token:
        logger.info("Telegram token not configured; alert for chat %s (message not logged)", chat_id)
        return True  # Local/testing behaviour, no network call.

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(url, json=payload)
        except httpx.HTTPError:
            logger.exception("Telegram request failed")
            return False

    if resp.status_code != 200:
        # Do not log the bot token or the full response body.
        logger.warning("Telegram rejected the message (status %s)", resp.status_code)
        return False
    return True
