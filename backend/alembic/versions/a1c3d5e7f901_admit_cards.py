"""admit cards table

Revision ID: a1c3d5e7f901
Revises: 77d6916446a3
Create Date: 2026-11-17

New table for admit-card / exam-city intimation notices — deliberately apart
from ``exam_notifications`` (no eligibility, no application window, different
expiry semantics). Nothing existing is altered.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c3d5e7f901"
down_revision: Union[str, Sequence[str], None] = "77d6916446a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admit_cards",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("organizing_body", sa.String(100), nullable=False),
        sa.Column("exam_name", sa.String(255), nullable=True),
        sa.Column("notification_date", sa.Date(), nullable=True),
        sa.Column("exam_date", sa.Date(), nullable=True),
        sa.Column("admit_url", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("last_checked_at", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_table("admit_cards")
