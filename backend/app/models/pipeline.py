# app/models/pipeline.py
"""Layer 1 (Discovery) persistence models.

Three tables back the scraper worker:

* ``scrape_sources`` — the registry of sites we poll. Carries tier, fetch
  mode, the css_selector used to scope content hashing (so volatile page
  chrome cannot flap the hash), and the failure/backoff bookkeeping.
* ``scrape_logs`` — one row per poll run, including no-change runs, so the
  48-hour stability test and per-source failure accounting have data.
* ``raw_discovered_links`` — every new notification/PDF URL the worker sees,
  deduplicated per source. Layer 2 (LLM extraction) reads from here.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.exam import Base


class ScrapeSource(Base):
    __tablename__ = "scrape_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    # 1 = poll frequently, 2 = moderate, 3 = slow-moving (daily-ish).
    tier: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # httpx (plain GET + BeautifulSoup), playwright (rendered DOM), or
    # json_api (a JSON endpoint behind a JS frontend; seeded with the query
    # params and URL template in ``config``).
    fetch_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="httpx")
    # Scopes both hashing and link extraction. NULL = whole page.
    css_selector: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Extra selector for volatile nodes to strip before hashing (visitor
    # counters, live clocks, rotating banners) in addition to the built-ins
    # (script/style/noscript/HTML comments).
    ignore_selector: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Optional regex; only links matching it are recorded in
    # raw_discovered_links. NULL = keep every http(s) link in scope.
    link_pattern: Mapped[str | None] = mapped_column(Text, nullable=True)
    # json_api settings: params, items_path, title_field, attachments_field,
    # file_url_template. Unused for html modes.
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Conditional-GET caching — 304 means "nothing changed" at ~0 cost.
    etag: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_modified: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Zero extracted/kept links for N consecutive *successful* runs.
    consecutive_zero_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    backoff_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    logs: Mapped[list["ScrapeLog"]] = relationship(back_populates="source")
    discovered_links: Mapped[list["RawDiscoveredLink"]] = relationship(back_populates="source")


class ScrapeLog(Base):
    __tablename__ = "scrape_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("scrape_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ok: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # False when the scoped content hash matched the previous run; the worker
    # then does no link extraction or LLM work at all.
    changed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    links_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_links: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[ScrapeSource] = relationship(back_populates="logs")


class RawDiscoveredLink(Base):
    __tablename__ = "raw_discovered_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("scrape_sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # new → picked up by Layer 2; processed → extracted into exam_notifications;
    # ignored → not a notification (matched a filter or failed validation).
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new")
    # Official publish time when the source exposes it (e.g. SSC JSON API
    # createdAt) — times the publish→listing lag metric.
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Cross-source dedup key, e.g. "13-2026" from "Advt 13-2026" / "CGL 2026/13".
    dedup_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("source_id", "url", name="uq_raw_discovered_links_source_url"),)

    source: Mapped[ScrapeSource] = relationship(back_populates="discovered_links")


class ExtractionResult(Base):
    """Layer 2 output: what the LLM read, how sure it was, and what a human
    should see. ``status='review'`` rows are never surfaced as a definitive
    eligibility result — the UI shows "Check notification" with the PDF link."""

    __tablename__ = "extraction_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_link_id: Mapped[int] = mapped_column(
        ForeignKey("raw_discovered_links.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    # auto → published; review → needs human check; rejected → junk document.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="review")
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Flat values: total_vacancies, age_max_general, age_relaxations, ...
    extracted: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    field_confidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    missing_fields: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    exam_notification_id: Mapped[str | None] = mapped_column(
        ForeignKey("exam_notifications.id", ondelete="SET NULL"), nullable=True
    )
