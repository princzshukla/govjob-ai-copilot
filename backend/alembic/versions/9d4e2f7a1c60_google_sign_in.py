"""google sign-in support

Revision ID: 9d4e2f7a1c60
Revises: b7c8d9e0f1a2
Create Date: 2026-11-20 08:20:00.000000

Google-only accounts have no password, so ``users.password_hash`` becomes
nullable. The stable Google ``sub`` claim is stored in a new unique column —
email is deliberately NOT used as the identity key because it can change.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "9d4e2f7a1c60"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.add_column("users", sa.Column("google_sub", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_users_google_sub", "users", ["google_sub"])


def downgrade() -> None:
    op.drop_constraint("uq_users_google_sub", "users", type_="unique")
    op.drop_column("users", "google_sub")
    # Restoring NOT NULL on password_hash would require inventing or deleting
    # Google-only users, so it is intentionally left nullable on downgrade.
