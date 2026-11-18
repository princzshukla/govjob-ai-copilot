"""notification discovery queue

Revision ID: f1a2b3c4d5e6
Revises: e8a1d3c5b724
Create Date: 2026-11-18

Research queue for unmatched aggregator entries. No existing table is
modified; discoveries are promoted into SEED_ADMIT_CARDS by admin action.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e8a1d3c5b724"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_discovery_queue",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("aggregator_title", sa.String(500), nullable=False),
        sa.Column("aggregator_url", sa.Text(), nullable=False, unique=True),
        sa.Column("organization", sa.String(120), nullable=True),
        sa.Column("recruitment_year", sa.String(4), nullable=True),
        sa.Column("notice_subtype", sa.String(30), nullable=True),
        sa.Column("official_website", sa.Text(), nullable=True),
        sa.Column("official_notification_url", sa.Text(), nullable=True),
        sa.Column("official_pdf_url", sa.Text(), nullable=True),
        sa.Column("extracted_information", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("verification_status", sa.String(30), nullable=False,
                  server_default="unverified"),
        sa.Column("discovery_status", sa.String(30), nullable=False,
                  server_default="discovered"),
        sa.Column("duplicate_reference", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_notification_discovery_status", "notification_discovery_queue", ["discovery_status"])
    op.create_table(
        "discovery_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("discovery_id", sa.Integer(),
                  sa.ForeignKey("notification_discovery_queue.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("from_status", sa.String(30), nullable=True),
        sa.Column("to_status", sa.String(30), nullable=False),
        sa.Column("actor", sa.String(120), nullable=False, server_default="system"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_discovery_history_discovery_id", "discovery_history", ["discovery_id"])


def downgrade() -> None:
    op.drop_table("discovery_history")
    op.drop_table("notification_discovery_queue")
