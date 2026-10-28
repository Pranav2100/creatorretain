"""give every user a session generation

Revision ID: b5f18e2ac904
Revises: a7c3d019f4be
Create Date: 2026-10-22 02:40:00.000000

Changing a password has to end the sessions that were opened with
the old one, and a JWT cannot be withdrawn once it is issued. So
each token carries the generation it was minted in, and a user
whose password changes moves on a generation.

Everyone starts at zero, and a token issued before this column
existed carries no generation at all and reads as zero too - so
applying this signs nobody out.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b5f18e2ac904"
down_revision: Union[str, Sequence[str], None] = "a7c3d019f4be"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "token_version")
