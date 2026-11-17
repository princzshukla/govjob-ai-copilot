"""extraction_results.admit_card_id

Revision ID: b2d4e6f8a012
Revises: a1c3d5e7f901
Create Date: 2026-11-17

Admit-card extractions are stored in ``extraction_results`` alongside job
notifications (same audit trail, review queue and trust pipeline); they are
told apart by ``extracted->>'kind' = 'admit_card'``. Once promoted they point
at their ``admit_cards`` row through this column. Jobs keep using
``exam_notification_id``; each row uses exactly one.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2d4e6f8a012"
down_revision: Union[str, Sequence[str], None] = "a1c3d5e7f901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "extraction_results",
        sa.Column(
            "admit_card_id",
            sa.String(36),
            sa.ForeignKey("admit_cards.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("extraction_results", "admit_card_id")
