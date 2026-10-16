"""add website_url to workspaces

Revision ID: f7c2a1b35e09
Revises: d41a6b70c925
Create Date: 2026-10-17 01:45:00.000000

Part of giving a hiring workspace a public face. The other fields
it needs - legal_name, bio, logo_url - already existed and were
simply never writable.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f7c2a1b35e09"
down_revision: Union[str, Sequence[str], None] = "d41a6b70c925"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "workspaces",
        sa.Column("website_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("workspaces", "website_url")
