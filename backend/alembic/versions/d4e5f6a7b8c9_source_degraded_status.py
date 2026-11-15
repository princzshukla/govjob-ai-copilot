"""scrape_sources health status ('ok' | 'degraded' | 'disabled')

Revision ID: d4e5f6a7b8c9
Revises: c5f8a1b2d3e6
Create Date: 2026-11-15

One first-class status per source so a flapping or 503ing source is *visible*
instead of dying silently inside a failure counter. ``degraded`` is set when
``consecutive_failures`` first reaches ``FAILURE_ALERT_THRESHOLD`` and cleared
on the next successful poll (or a 304). ``disabled`` is set when a source is
hard-stopped (robots.txt). ``ok`` is the steady state.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c5f8a1b2d3e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scrape_sources",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ok"),
    )
    op.create_index("ix_scrape_sources_status", "scrape_sources", ["status"])


def downgrade() -> None:
    op.drop_index("ix_scrape_sources_status", table_name="scrape_sources")
    op.drop_column("scrape_sources", "status")
