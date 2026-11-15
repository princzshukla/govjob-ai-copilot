"""extraction_cache: reuse LLM extractions by PDF content hash

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-11-15

The benchmark and the discovery poller re-see the same advertisement PDFs
(e.g. the benchmark suite, or the same ad linked by two sources with
different URLs). Caching the *trusted* (status='auto') extractions by
sha256(pdf_bytes) removes those LLM calls entirely. 'review' results are
deliberately NOT cached: a review verdict may become 'auto' after the
extractor is improved, and caching would freeze the bad verdict.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "extraction_cache",
        sa.Column("content_hash", sa.String(length=64), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="auto"),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_extraction_cache_status", "extraction_cache", ["status"])


def downgrade() -> None:
    op.drop_index("ix_extraction_cache_status", table_name="extraction_cache")
    op.drop_table("extraction_cache")
