"""worker budget + link process attempts

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-11-15

Two additions so the Layer 2 worker can run unattended without blowing the
free LLM tier or looping forever on a dead link:

* ``raw_discovered_links.process_attempts`` — how many times the worker
  tried a link. Links that fail 3 times are skipped (with a log line).
* ``token_budget`` — one row per UTC day, running token estimate used by the
  worker. The worker stops cleanly when the budget is hit (env
  ``WORKER_DAILY_TOKEN_BUDGET``, default 40000).
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "raw_discovered_links",
        sa.Column("process_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "token_budget",
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("tokens_used", sa.BigInteger(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("token_budget")
    op.drop_column("raw_discovered_links", "process_attempts")
