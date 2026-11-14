"""extraction review state + discovery reliability metrics

Revision ID: c5f8a1b2d3e6
Revises: b3e1f7a92c04
Create Date: 2026-11-14

Step 2 (trust) — ``extraction_results`` stores every Layer-2 extraction with
per-field confidence + verbatim evidence snippets, and a ``status`` of
``auto`` (published), ``review`` (shown as "Check notification", never as a
definitive eligibility result) or ``rejected``. Each row links back to the
discovered link and forward to the published exam_notification when promoted.

Step 4 (reliability) —
* ``scrape_sources`` gains ``etag``/``last_modified`` (conditional GET; a
  304 means "nothing changed" at negligible cost) and
  ``consecutive_zero_runs`` (zero-links-for-N-runs health alarm).
* ``scrape_logs`` gains ``note`` (e.g. ``not-modified(304)``,
  ``robots-disallowed``).
* ``raw_discovered_links`` gains ``published_at`` (official publish time,
  when the source exposes it — drives the publish→listing latency metric)
  and ``dedup_key`` (advertisement-number key for cross-source dedup).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5f8a1b2d3e6"
down_revision: Union[str, Sequence[str], None] = "b3e1f7a92c04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scrape_sources", sa.Column("etag", sa.Text(), nullable=True))
    op.add_column("scrape_sources", sa.Column("last_modified", sa.Text(), nullable=True))
    op.add_column(
        "scrape_sources",
        sa.Column("consecutive_zero_runs", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("scrape_logs", sa.Column("note", sa.Text(), nullable=True))
    op.add_column(
        "raw_discovered_links",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("raw_discovered_links", sa.Column("dedup_key", sa.Text(), nullable=True))
    op.create_index("ix_raw_discovered_links_dedup_key", "raw_discovered_links", ["dedup_key"])

    op.create_table(
        "extraction_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "raw_link_id",
            sa.Integer(),
            sa.ForeignKey("raw_discovered_links.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        # auto → extracted & published; review → shown as "Check notification";
        # rejected → wrong/junk document (e.g. admit card, corrupt PDF).
        sa.Column("status", sa.String(length=20), nullable=False, server_default="review"),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("extracted", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("field_confidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("missing_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(length=120), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column(
            "exam_notification_id",
            sa.String(length=100),
            sa.ForeignKey("exam_notifications.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_extraction_results_status", "extraction_results", ["status"])


def downgrade() -> None:
    op.drop_index("ix_extraction_results_status", table_name="extraction_results")
    op.drop_table("extraction_results")
    op.drop_index("ix_raw_discovered_links_dedup_key", table_name="raw_discovered_links")
    op.drop_column("raw_discovered_links", "dedup_key")
    op.drop_column("raw_discovered_links", "published_at")
    op.drop_column("scrape_logs", "note")
    op.drop_column("scrape_sources", "consecutive_zero_runs")
    op.drop_column("scrape_sources", "last_modified")
    op.drop_column("scrape_sources", "etag")
