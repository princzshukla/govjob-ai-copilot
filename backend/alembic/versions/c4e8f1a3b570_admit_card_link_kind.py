"""admit_cards.link_kind

Revision ID: c4e8f1a3b570
Revises: b2d4e6f8a012
Create Date: 2026-11-18

Admit-card links are not all the same kind of thing:
- ``notice_pdf``      — direct official notice PDF (rare; boards usually ship this on the site of the exam body)
- ``notice_page``     — official page on the board's own portal (e.g. UPSC What's New detail page)
- ``candidate_portal``— official candidate-login portal where the card is downloaded (most boards; the admit card itself is never public)

So the UI never labels a login portal as a "Download" link. Existing rows default to ``notice_pdf``; the seed refresh corrects them on next boot.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4e8f1a3b570"
down_revision: Union[str, Sequence[str], None] = "b2d4e6f8a012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "admit_cards",
        sa.Column("link_kind", sa.String(20), nullable=False, server_default="notice_pdf"),
    )


def downgrade() -> None:
    op.drop_column("admit_cards", "link_kind")
