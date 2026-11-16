"""restore exam_notifications verification columns

Revision ID: 77d6916446a3
Revises: f6a7b8c9d0e1
Create Date: 2026-11-16 12:18:39.585296

The original (pre-migration) dev database carries three provenance columns
that never existed in this repo's history but that no code should lose:

- verification_status: 'verified' (51 rows) / 'check_required' (5 rows)
- verified_on: date the row was verified against its source
- apply_url: official application portal URL (50 rows)

This migration restores them to the schema so a fresh database matches the
long-lived dev database, instead of dropping that provenance. Both sides
also carry them nullable, and nothing reads them yet.

SQL uses IF NOT EXISTS so the long-lived dev database (where the columns
already exist) applies this migration as a no-op rather than failing.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "77d6916446a3"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE exam_notifications ADD COLUMN IF NOT EXISTS apply_url TEXT")
    op.execute(
        "ALTER TABLE exam_notifications ADD COLUMN IF NOT EXISTS verification_status VARCHAR(20)"
    )
    op.execute("ALTER TABLE exam_notifications ADD COLUMN IF NOT EXISTS verified_on DATE")


def downgrade() -> None:
    op.execute("ALTER TABLE exam_notifications DROP COLUMN IF EXISTS verified_on")
    op.execute("ALTER TABLE exam_notifications DROP COLUMN IF EXISTS verification_status")
    op.execute("ALTER TABLE exam_notifications DROP COLUMN IF EXISTS apply_url")
