# app/models/admit_card.py
from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.exam import Base


class AdmitCardNotification(Base):
    """An admit card / exam-city intimation notice published by a govt board.

    Deliberately a separate table from ``exam_notifications``: an admit card
    has no eligibility criteria and no application window, so the eligibility
    engine and the deadline-driven ``window_state`` logic must never see it.

    ``admit_url`` is whatever the board published — a PDF *or* a page that
    links the PDF / login portal. It is only ever an official link captured
    from the board's own notice; never constructed, never from a third party.
    Rows go inactive once ``exam_date`` passes (or 60 days after
    ``notification_date`` when no exam date is published) — see
    ``expire_stale_admit_cards`` in app/core/tasks.py.
    """

    __tablename__ = "admit_cards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    organizing_body: Mapped[str] = mapped_column(String(100), nullable=False)
    exam_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # notice_pdf | notice_page | candidate_portal — what admit_url actually is
    link_kind: Mapped[str] = mapped_column(String(20), default="notice_pdf", nullable=False)

    notification_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    exam_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    admit_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_checked_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
