"""layer 1 discovery pipeline schema

Revision ID: b3e1f7a92c04
Revises: f47c2a9d1b08
Create Date: 2026-11-13

Adds the Layer 1 (Discovery) tables owned by the scraper worker:

* ``scrape_sources`` — poll registry: tier, fetch mode, scoping selector,
  failure/backoff bookkeeping, last content hash.
* ``scrape_logs`` — one row per poll run (including no-change runs).
* ``raw_discovered_links`` — new notification/PDF URLs per source,
  deduplicated on (source_id, url). This is the hand-off queue for Layer 2
  (LLM extraction).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3e1f7a92c04"
down_revision: Union[str, Sequence[str], None] = "f47c2a9d1b08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scrape_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("fetch_mode", sa.String(length=20), nullable=False, server_default="httpx"),
        sa.Column("css_selector", sa.Text(), nullable=True),
        sa.Column("ignore_selector", sa.Text(), nullable=True),
        sa.Column("link_pattern", sa.Text(), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("interval_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("backoff_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_hash", sa.String(length=64), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "scrape_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("scrape_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ok", sa.Boolean(), nullable=False),
        sa.Column("changed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("links_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("new_links", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_scrape_logs_source_id", "scrape_logs", ["source_id"])

    op.create_table(
        "raw_discovered_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("scrape_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="new"),
        sa.UniqueConstraint("source_id", "url", name="uq_raw_discovered_links_source_url"),
    )
    op.create_index("ix_raw_discovered_links_source_id", "raw_discovered_links", ["source_id"])


def downgrade() -> None:
    op.drop_index("ix_raw_discovered_links_source_id", table_name="raw_discovered_links")
    op.drop_table("raw_discovered_links")
    op.drop_index("ix_scrape_logs_source_id", table_name="scrape_logs")
    op.drop_table("scrape_logs")
    op.drop_table("scrape_sources")
