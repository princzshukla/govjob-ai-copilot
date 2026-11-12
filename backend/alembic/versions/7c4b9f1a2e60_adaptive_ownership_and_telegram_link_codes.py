"""adaptive ownership and telegram link codes

Revision ID: 7c4b9f1a2e60
Revises: 2ffb5e9a2d9c
Create Date: 2026-11-12 17:05:00.000000

Phase 2 ownership, part two:

* ``topic_mastery.user_id`` and ``quiz_attempts.user_id`` become INTEGER
  foreign keys to ``users.id`` with ``ON DELETE CASCADE``. They were free-form
  strings, so the API could not prove who owned an attempt.
* ``telegram_link_codes`` stores the short-lived, single-use codes used to
  verify a Telegram chat. The verified chat itself still lives in
  ``telegram_links`` (added in Phase 1).

Existing adaptive rows are only convertible when their string id is exactly the
text form of an existing ``users.id``. Rather than guess, this revision deletes
the known demo rows and then refuses to run if any other row has no account.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c4b9f1a2e60"
down_revision: Union[str, Sequence[str], None] = "2ffb5e9a2d9c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# The placeholder id the old API used when no session existed. These rows
# cannot belong to a real account and are safe to drop.
_DEMO_USER_ID = "usr_demo_001"

_ORPHAN_COUNT_SQL = sa.text(
    """
    SELECT
      (SELECT count(*) FROM topic_mastery tm
        WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id::text = tm.user_id))
    +
      (SELECT count(*) FROM quiz_attempts qa
        WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id::text = qa.user_id))
    """
)


def _delete_demo_rows() -> None:
    op.execute(
        sa.text("DELETE FROM topic_mastery WHERE user_id = :demo").bindparams(
            demo=_DEMO_USER_ID
        )
    )
    op.execute(
        sa.text("DELETE FROM quiz_attempts WHERE user_id = :demo").bindparams(
            demo=_DEMO_USER_ID
        )
    )


def _assert_all_rows_have_an_account() -> None:
    """Fail loudly instead of casting an unmappable string id.

    ``u.id::text = tm.user_id`` also rejects non-numeric values, so a later
    ``user_id::integer`` cannot raise a raw cast error halfway through.
    """
    orphans = op.get_bind().execute(_ORPHAN_COUNT_SQL).scalar_one()
    if orphans:
        raise RuntimeError(
            f"{orphans} adaptive row(s) have a user_id that is not an existing "
            "users.id. This migration converts those columns to INTEGER foreign "
            "keys, so map or delete those rows (ownership must be decided "
            "explicitly) before running `alembic upgrade head` again."
        )


def upgrade() -> None:
    """Upgrade schema."""
    _delete_demo_rows()
    _assert_all_rows_have_an_account()

    op.alter_column(
        "topic_mastery",
        "user_id",
        existing_type=sa.String(),
        type_=sa.Integer(),
        postgresql_using="user_id::integer",
    )
    op.alter_column(
        "quiz_attempts",
        "user_id",
        existing_type=sa.String(),
        type_=sa.Integer(),
        postgresql_using="user_id::integer",
    )

    op.create_foreign_key(
        "fk_topic_mastery_user_id",
        "topic_mastery",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_quiz_attempts_user_id",
        "quiz_attempts",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_table(
        "telegram_link_codes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_telegram_link_codes_user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_telegram_link_codes_user_id"),
        sa.UniqueConstraint("code_hash", name="uq_telegram_link_codes_code_hash"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("telegram_link_codes")

    op.drop_constraint(
        "fk_quiz_attempts_user_id", "quiz_attempts", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_topic_mastery_user_id", "topic_mastery", type_="foreignkey"
    )

    op.alter_column(
        "quiz_attempts",
        "user_id",
        existing_type=sa.Integer(),
        type_=sa.String(),
        postgresql_using="user_id::varchar",
    )
    op.alter_column(
        "topic_mastery",
        "user_id",
        existing_type=sa.Integer(),
        type_=sa.String(),
        postgresql_using="user_id::varchar",
    )
