"""question reports: one report per (question, user)

Revision ID: b7c8d9e0f1a2
Revises: a2b3c4d5e6f7
Create Date: 2026-11-19

Adds the durable dedup table needed by /report-question so a single account
cannot retire a shared question by calling the endpoint three times.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "question_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column(
            "question_id",
            sa.String(),
            sa.ForeignKey(
                "question_bank.id",
                ondelete="CASCADE",
                name="fk_question_reports_question_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                ondelete="CASCADE",
                name="fk_question_reports_user_id",
            ),
            nullable=False,
        ),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "question_id", "user_id", name="uq_question_reports_question_user"
        ),
    )
    op.create_index(
        "ix_question_reports_question_id", "question_reports", ["question_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_question_reports_question_id", table_name="question_reports")
    op.drop_table("question_reports")
