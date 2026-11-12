"""relax NOT NULL on draftable profile fields

Revision ID: 5a2c9e31d4b8
Revises: 7c4b9f1a2e60
Create Date: 2026-11-12 17:00:00.000000

Phase 4 lets a guest claim an incomplete resume draft after sign-in, and lets an
account save a partial profile at any time. ``candidate_profiles.dob``,
``domicile_state`` and ``highest_degree`` were NOT NULL, which made every
incomplete draft unsavable (an INSERT would fail with a 500). Dropping NOT NULL
is non-destructive.

The downgrade re-adds NOT NULL. That is expected to fail on any database
containing partial profiles; it is not silently edited to force the data into
shape.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5a2c9e31d4b8"
down_revision: Union[str, Sequence[str], None] = "7c4b9f1a2e60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = ("dob", "domicile_state", "highest_degree")


def upgrade() -> None:
    with op.batch_alter_table("candidate_profiles") as batch_op:
        batch_op.alter_column("dob", existing_type=sa.Date(), nullable=True)
        batch_op.alter_column("domicile_state", existing_type=sa.String(length=50), nullable=True)
        batch_op.alter_column("highest_degree", existing_type=sa.String(length=100), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("candidate_profiles") as batch_op:
        batch_op.alter_column("highest_degree", existing_type=sa.String(length=100), nullable=False)
        batch_op.alter_column("domicile_state", existing_type=sa.String(length=50), nullable=False)
        batch_op.alter_column("dob", existing_type=sa.Date(), nullable=False)
