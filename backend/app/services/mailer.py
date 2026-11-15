# app/services/mailer.py
"""Optional SMTP digest for newly-published exams.

Dormant unless ``MAIL_PROVIDER=smtp`` and ``MAIL_DIGEST_TO`` are set. Any
failure is logged and swallowed — sending mail must never break the publish
path.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def _recipients() -> list[str]:
    return [r.strip() for r in settings.MAIL_DIGEST_TO.split(",") if r.strip()]


def mail_enabled() -> bool:
    return settings.MAIL_PROVIDER.strip().lower() == "smtp" and bool(_recipients())


def send_exam_digest(promoted: list[dict]) -> bool:
    """Send one digest listing exams promoted since the worker ran.

    ``promoted`` items: ``{title, organizing_body, application_deadline,
    official_pdf_url}``. Returns True if a message was sent.
    """
    if not promoted:
        return False
    if not mail_enabled():
        logger.info("mail digest skipped (MAIL_PROVIDER/MAIL_DIGEST_TO not set); %d exam(s) would be listed", len(promoted))
        return False
    if not settings.MAIL_SMTP_HOST:
        logger.warning("MAIL_PROVIDER=smtp but MAIL_SMTP_HOST is empty — skipping digest")
        return False

    lines = ["GovJob Matcher: new exams published from official notifications", ""]
    for e in promoted:
        lines.append(f"- {e['title']} — {e['organizing_body']}")
        lines.append(f"  Deadline: {e['application_deadline']}  |  PDF: {e['official_pdf_url']}")
    body = "\n".join(lines) + "\n"

    message = EmailMessage()
    message["Subject"] = f"GovJob: {len(promoted)} new exam(s) published"
    message["From"] = settings.MAIL_FROM
    message["To"] = ", ".join(_recipients())
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.MAIL_SMTP_HOST, settings.MAIL_SMTP_PORT, timeout=settings.MAIL_TIMEOUT_SECONDS) as smtp:
            smtp.starttls()
            if settings.MAIL_SMTP_USER:
                smtp.login(settings.MAIL_SMTP_USER, settings.MAIL_SMTP_PASS)
            smtp.send_message(message)
        logger.info("mail digest sent to %d recipient(s)", len(_recipients()))
        return True
    except Exception:
        logger.exception("mail digest failed — publish path unaffected")
        return False
