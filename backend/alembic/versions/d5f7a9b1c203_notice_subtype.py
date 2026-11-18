"""admit_cards.notice_subtype

Revision ID: d5f7a9b1c203
Revises: c4e8f1a3b570
Create Date: 2026-11-18

Exam-city intimations are not admit cards. Keep the subtype on the row so the
feed can filter/label them separately while reusing one storage model.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d5f7a9b1c203"
down_revision: Union[str, Sequence[str], None] = "c4e8f1a3b570"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "admit_cards",
        sa.Column("notice_subtype", sa.String(20), nullable=False, server_default="admit_card"),
    )


def downgrade() -> None:
    op.drop_column("admit_cards", "notice_subtype")
