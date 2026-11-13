"""eligibility engine schema

Revision ID: f47c2a9d1b08
Revises: 6f5be5e32e17
Create Date: 2026-11-13

Captures the schema owned by the candidate-profile / eligibility work:

* ``exam_notifications`` gains ``topics``, ``allows_final_year``,
  ``max_attempts``, ``source_url`` and ``last_checked_at``.
* ``candidate_profiles`` gains ``graduation_status`` and ``previous_attempts``.
  ``user_id`` loses NOT NULL: a profile saved by a guest before sign-up has no
  owner. Account-owned rows keep their id, so the unique constraint on
  ``user_id`` still enforces at most one owned profile per account (Postgres
  allows any number of NULLs in a unique column).
* ``eligibility_reports`` is new ("report a wrong eligibility result").
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f47c2a9d1b08"
down_revision: Union[str, Sequence[str], None] = "6f5be5e32e17"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "exam_notifications",
        sa.Column("topics", postgresql.ARRAY(sa.String()), nullable=True),
    )
    op.add_column(
        "exam_notifications",
        sa.Column("allows_final_year", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "exam_notifications",
        sa.Column("max_attempts", sa.Integer(), nullable=True),
    )
    op.add_column(
        "exam_notifications",
        sa.Column("source_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "exam_notifications",
        sa.Column("last_checked_at", sa.Date(), nullable=True),
    )

    op.add_column(
        "candidate_profiles",
        sa.Column(
            "graduation_status",
            sa.String(length=30),
            server_default="Completed",
            nullable=False,
        ),
    )
    op.add_column(
        "candidate_profiles",
        sa.Column(
            "previous_attempts",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    # Guest profiles have no owner; NULL passes the unique constraint.
    op.alter_column(
        "candidate_profiles",
        "user_id",
        existing_type=sa.Integer(),
        nullable=True,
    )

    op.create_table(
        "eligibility_reports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("exam_id", sa.String(length=100), nullable=False),
        sa.Column("reported_verdict", sa.String(length=20), nullable=True),
        sa.Column("expected_verdict", sa.String(length=20), nullable=True),
        sa.Column("candidate_snapshot", sa.JSON(), nullable=False),
        sa.Column("exam_snapshot", sa.JSON(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_eligibility_reports_exam_id",
        "eligibility_reports",
        ["exam_id"],
    )

    # Adaptive engine (branch work): provenance, grounding and telemetry on
    # questions, plus net_marks on attempts.
    op.add_column(
        "question_bank",
        sa.Column("origin_type", sa.String(), server_default="PYQ_STYLE", nullable=True),
    )
    op.add_column("question_bank", sa.Column("pyq_year", sa.Integer(), nullable=True))
    op.add_column(
        "question_bank",
        sa.Column("ai_difficulty", sa.String(), server_default="Medium", nullable=True),
    )
    op.add_column(
        "question_bank", sa.Column("calibrated_difficulty", sa.String(), nullable=True)
    )
    op.add_column("question_bank", sa.Column("source_title", sa.String(), nullable=True))
    op.add_column("question_bank", sa.Column("source_date", sa.String(), nullable=True))
    op.add_column("question_bank", sa.Column("ca_month", sa.String(length=7), nullable=True))
    op.create_index("ix_question_bank_ca_month", "question_bank", ["ca_month"])
    op.add_column(
        "question_bank",
        sa.Column("attempts_count", sa.Integer(), server_default="0", nullable=True),
    )
    op.add_column(
        "question_bank",
        sa.Column("correct_count", sa.Integer(), server_default="0", nullable=True),
    )
    op.add_column(
        "question_bank",
        sa.Column("avg_time_sec", sa.Float(), server_default="45.0", nullable=True),
    )
    op.add_column(
        "question_bank",
        sa.Column("report_count", sa.Integer(), server_default="0", nullable=True),
    )
    op.add_column(
        "question_bank",
        sa.Column("quality_score", sa.Float(), server_default="1.0", nullable=True),
    )
    op.add_column(
        "question_bank",
        sa.Column(
            "is_retired",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=True,
        ),
    )
    op.create_index("ix_question_bank_is_retired", "question_bank", ["is_retired"])
    op.add_column(
        "quiz_attempts",
        sa.Column("net_marks", sa.Float(), server_default="0", nullable=True),
    )


def downgrade() -> None:
    op.drop_column("quiz_attempts", "net_marks")

    op.drop_index("ix_question_bank_is_retired", table_name="question_bank")
    op.drop_column("question_bank", "is_retired")
    op.drop_column("question_bank", "quality_score")
    op.drop_column("question_bank", "report_count")
    op.drop_column("question_bank", "avg_time_sec")
    op.drop_column("question_bank", "correct_count")
    op.drop_column("question_bank", "attempts_count")
    op.drop_index("ix_question_bank_ca_month", table_name="question_bank")
    op.drop_column("question_bank", "ca_month")
    op.drop_column("question_bank", "source_date")
    op.drop_column("question_bank", "source_title")
    op.drop_column("question_bank", "calibrated_difficulty")
    op.drop_column("question_bank", "ai_difficulty")
    op.drop_column("question_bank", "pyq_year")
    op.drop_column("question_bank", "origin_type")

    op.drop_index("ix_eligibility_reports_exam_id", table_name="eligibility_reports")
    op.drop_table("eligibility_reports")

    op.alter_column(
        "candidate_profiles",
        "user_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.drop_column("candidate_profiles", "previous_attempts")
    op.drop_column("candidate_profiles", "graduation_status")

    op.drop_column("exam_notifications", "last_checked_at")
    op.drop_column("exam_notifications", "source_url")
    op.drop_column("exam_notifications", "max_attempts")
    op.drop_column("exam_notifications", "allows_final_year")
    op.drop_column("exam_notifications", "topics")
