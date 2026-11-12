"""Minimal structured logging.

Production (ENVIRONMENT=production) emits one JSON object per line so logs can
be scraped by Loki/CloudWatch/etc. Dev and tests get a human-readable line.

Nothing in the codebase logs passwords, tokens or resume text; keep it that
way — this module formats, it does not redact.
"""

import json
import logging
import os
from datetime import datetime, timezone

_LOG_FORMAT = "%(levelname)s [%(name)s] %(message)s"


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

    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)

    configure_logging._done = True  # type: ignore[attr-defined]
