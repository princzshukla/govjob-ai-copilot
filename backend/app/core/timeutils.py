"""Shared time helpers.

Indian Standard Time is a fixed UTC+05:30 offset (no daylight saving), so a
plain ``timezone(timedelta(hours=5, minutes=30))`` is exact and does not
depend on the host's tz database.
"""

from datetime import date, datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def today_ist() -> date:
    """Current calendar date in India (UTC+05:30)."""
    return datetime.now(IST).date()


def deadline_open(application_deadline: date | None, today: date) -> bool:
    """True while a job's application window is open (IST, end-of-day).

    A deadline of ``today`` is still open; ``yesterday`` is closed. A missing
    deadline is never treated as expired — the row stays visible and the UI
    shows "check official notification" instead of a hard date.
    """
    if application_deadline is None:
        return True
    return application_deadline >= today
