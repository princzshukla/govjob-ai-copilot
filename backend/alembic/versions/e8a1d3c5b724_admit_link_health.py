"""admit_cards link-health bookkeeping

Revision ID: e8a1d3c5b724
Revises: d5f7a9b1c203
Create Date: 2026-11-18

Adds a persisted consecutive-failure counter and an operator-readable note
so the weekly link sweeper can require repeated confirmed failures before
hiding a card. Also records why a row was restored.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "e8a1d3c5b724"
down_revision: Union[str, Sequence[str], None] = "d5f7a9b1c203"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "admit_cards",
        sa.Column("link_fail_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("admit_cards", sa.Column("link_health_note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("admit_cards", "link_health_note")
    op.drop_column("admit_cards", "link_fail_count")
