"""add resend_requested_at to workspace invitations

Revision ID: c3f81a04d7be
Revises: 1588da68d49f
Create Date: 2026-09-06 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3f81a04d7be"
down_revision: Union[str, Sequence[str], None] = "1588da68d49f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "workspace_invitations",
        sa.Column(
            "resend_requested_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column(
        "workspace_invitations",
        "resend_requested_at",
    )
