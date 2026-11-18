"""Minimal structured logging.

Production (ENVIRONMENT=production) emits one JSON object per line so logs can
be scraped by Loki/CloudWatch/etc. Dev and tests get a human-readable line.

Secrets are redacted at the handler (see RedactSecretsFilter) — this is the
last line of defence for bot tokens that third-party libraries may log.
"""

import json
import logging
import os
import re
from datetime import datetime, timezone


_LOG_FORMAT = "%(levelname)s [%(name)s] %(message)s"
_BOT_URL_RE = re.compile(r"bot\d+:[A-Za-z0-9_-]{20,}")


class RedactSecretsFilter(logging.Filter):
    """Scrub bot tokens from every log record (httpx logs request URLs)."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            text = record.getMessage()
        except Exception:
            return True
        redacted = _BOT_URL_RE.sub("bot***REDACTED_TOKEN***", text)
        try:
            from app.core.config import settings

            token = settings.TELEGRAM_BOT_TOKEN.strip()
            if token:
                redacted = redacted.replace(token, "***REDACTED_BOT_TOKEN***")
        except Exception:
            pass
        if redacted != text:
            record.msg = redacted
            record.args = ()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, str] = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    """Install one root handler; repeated calls are no-ops."""

    if getattr(configure_logging, "_done", False):
        return

    from app.core.config import settings

    root = logging.getLogger()
    root.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())

    handler = logging.StreamHandler()
    if settings.ENVIRONMENT == "production":
        formatter: logging.Formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(_LOG_FORMAT)
    handler.setFormatter(formatter)
    handler.addFilter(RedactSecretsFilter())

    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)

    # httpx logs URLs at INFO even before/without configure_logging; attach
    # the same filter to that logger too (e.g. CLI diagnostics).
    logging.getLogger("httpx").addFilter(RedactSecretsFilter())

    configure_logging._done = True  # type: ignore[attr-defined]
