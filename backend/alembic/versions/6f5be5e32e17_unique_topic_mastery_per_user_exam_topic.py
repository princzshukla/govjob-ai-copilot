"""unique mastery row per (user, exam, topic)

Revision ID: 6f5be5e32e17
Revises: 5a2c9e31d4b8
Create Date: 2026-11-12 18:30:00.000000

Two concurrent drills used to create duplicate ``topic_mastery`` rows for the
same ``(user_id, exam_id, topic)`` key, splitting the EMA. This revision
collapses duplicates (keeping the row with the most attempts, then the most
recent review) and adds the unique index. The application switched from
select-then-insert to ``ON CONFLICT DO UPDATE`` in the same change, so both
paths agree.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6f5be5e32e17"
down_revision: Union[str, Sequence[str], None] = "5a2c9e31d4b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        # Keep the strongest signal per (user_id, exam_id, topic).
        """
        DELETE FROM topic_mastery
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY user_id, exam_id, topic
                           ORDER BY attempts_count DESC NULLS LAST,
                                    last_reviewed_at DESC NULLS LAST,
                                    id
                       ) AS rn
                FROM topic_mastery
            ) ranked
            WHERE rn > 1
        )
        """
    )
    op.create_unique_constraint(
        "uq_topic_mastery_user_exam_topic",
        "topic_mastery",
        ["user_id", "exam_id", "topic"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_topic_mastery_user_exam_topic",
        "topic_mastery",
        type_="unique",
    )
