"""user ownership links and profile fields

Revision ID: 2ffb5e9a2d9c
Revises: 98d8dddbecd4
Create Date: 2026-11-12 15:35:20.531145

Adds the account-owned data model for Phase 1:

* ``users`` gains profile fields and verification timestamps.
* ``telegram_links`` is new and owned by a user; ``roadmap_progress`` is new and
  owned through its roadmap (``saved_roadmaps.user_id``), so ownership is stored
  exactly once.
* ``candidate_profiles`` and ``saved_roadmaps`` gain a NOT NULL ``user_id``
  with ``ON DELETE CASCADE``.

Neither of the latter two tables has ever been written by the application, so
this revision deliberately refuses to guess an owner: it fails loudly if either
table is not empty. Deciding ownership is a human/backfill decision, not
something a migration may invent.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2ffb5e9a2d9c"
down_revision: Union[str, Sequence[str], None] = "98d8dddbecd4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tables that gain a NOT NULL owner column in this revision.
_OWNER_TABLES = ("candidate_profiles", "saved_roadmaps")


def _assert_empty(table: str) -> None:
    """Fail loudly instead of silently orphaning or inventing an owner.

    Table/column identifiers are module constants, and ``sa.table`` quotes
    them, so no caller input reaches the SQL.
    """
    bind = op.get_bind()
    count = bind.execute(
        sa.select(sa.func.count()).select_from(sa.table(table))
    ).scalar_one()
    if count:
        raise RuntimeError(
            f"{table} contains {count} row(s) with no known owner. This "
            "migration adds a NOT NULL user_id to it, so those rows must be "
            "backfilled or deleted (with ownership decided explicitly) before "
            "running `alembic upgrade head` again."
        )


def upgrade() -> None:
    """Upgrade schema."""
    for table in _OWNER_TABLES:
        _assert_empty(table)

    # One verified Telegram chat per account. Chat ids only come from Telegram,
    # never from the client, so they are stored rather than derived.
    op.create_table(
        "telegram_links",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.String(length=64), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_telegram_links_user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_telegram_links_user_id"),
        sa.UniqueConstraint("chat_id", name="uq_telegram_links_chat_id"),
    )

    # "Week N of roadmap R is done". The composite primary key makes the write
    # idempotent. Ownership is derived from saved_roadmaps.user_id instead of
    # being copied here, so the two can never disagree; the roadmap FK cascades
    # from the user through saved_roadmaps.
    op.create_table(
        "roadmap_progress",
        sa.Column("roadmap_id", sa.String(length=36), nullable=False),
        sa.Column("week_no", sa.Integer(), nullable=False),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("week_no >= 1", name="ck_roadmap_progress_week_positive"),
        sa.ForeignKeyConstraint(
            ["roadmap_id"],
            ["saved_roadmaps.id"],
            name="fk_roadmap_progress_roadmap_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("roadmap_id", "week_no"),
    )

    # One candidate profile per account. The unique constraint also doubles as
    # the index backing the cascade on user delete.
    op.add_column(
        "candidate_profiles", sa.Column("user_id", sa.Integer(), nullable=False)
    )
    op.create_unique_constraint(
        "uq_candidate_profiles_user_id", "candidate_profiles", ["user_id"]
    )
    op.create_foreign_key(
        "fk_candidate_profiles_user_id",
        "candidate_profiles",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # One saved roadmap per account per exam (regenerating replaces it).
    op.add_column(
        "saved_roadmaps", sa.Column("user_id", sa.Integer(), nullable=False)
    )
    op.create_unique_constraint(
        "uq_saved_roadmaps_user_exam", "saved_roadmaps", ["user_id", "exam_id"]
    )
    op.create_foreign_key(
        "fk_saved_roadmaps_user_id",
        "saved_roadmaps",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.add_column(
        "users", sa.Column("full_name", sa.String(length=120), nullable=True)
    )
    op.add_column("users", sa.Column("phone", sa.String(length=20), nullable=True))
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_unique_constraint("uq_users_phone", "users", ["phone"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_users_phone", "users", type_="unique")
    op.drop_column("users", "updated_at")
    op.drop_column("users", "phone_verified_at")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "phone")
    op.drop_column("users", "full_name")

    op.drop_constraint(
        "fk_saved_roadmaps_user_id", "saved_roadmaps", type_="foreignkey"
    )
    op.drop_constraint(
        "uq_saved_roadmaps_user_exam", "saved_roadmaps", type_="unique"
    )
    op.drop_column("saved_roadmaps", "user_id")

    op.drop_constraint(
        "fk_candidate_profiles_user_id", "candidate_profiles", type_="foreignkey"
    )
    op.drop_constraint(
        "uq_candidate_profiles_user_id", "candidate_profiles", type_="unique"
    )
    op.drop_column("candidate_profiles", "user_id")

    op.drop_table("roadmap_progress")
    op.drop_table("telegram_links")
