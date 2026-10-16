"""add logo_storage_key to workspaces

Revision ID: a83f1c6de204
Revises: f7c2a1b35e09
Create Date: 2026-10-17 02:20:00.000000

A logo is now uploaded rather than linked, so the row has to
remember where the file actually lives. The public URL is not
enough: you cannot delete a CDN address, and replacing a logo
should not leave the old one behind.

Existing rows keep whatever logo_url they had and get a null key,
which reads correctly as "we did not put this file there".

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a83f1c6de204"
down_revision: Union[str, Sequence[str], None] = "f7c2a1b35e09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "workspaces",
        sa.Column(
            "logo_storage_key",
            sa.String(length=500),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("workspaces", "logo_storage_key")
