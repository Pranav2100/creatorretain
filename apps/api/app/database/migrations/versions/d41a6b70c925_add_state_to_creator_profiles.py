"""add state to creator profiles

Revision ID: d41a6b70c925
Revises: b2e7c91d84af
Create Date: 2026-10-15 01:40:00.000000

The region inside the country. Nullable and not part of the
completeness rule, because a creator in Singapore has nothing to
put here and should not be held back by an empty box.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d41a6b70c925"
down_revision: Union[str, Sequence[str], None] = "b2e7c91d84af"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "creator_profiles",
        sa.Column("state", sa.String(length=100), nullable=True),
    )

    op.create_index(
        op.f("ix_creator_profiles_state"),
        "creator_profiles",
        ["state"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_creator_profiles_state"),
        table_name="creator_profiles",
    )

    op.drop_column("creator_profiles", "state")
