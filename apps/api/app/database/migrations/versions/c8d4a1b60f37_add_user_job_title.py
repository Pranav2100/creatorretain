"""give a user a job title

Revision ID: c8d4a1b60f37
Revises: b5f18e2ac904
Create Date: 2026-10-22 03:20:00.000000

A creator deciding whether to take an offer should know who sent
it, not just which agency. That means the agency's people need
names a creator can read and a role that explains them - the
difference between "TalentX offered you this" and "Saloni
Deshmukh, Talent Manager at TalentX, offered you this".

Nullable, because the person who starts their own workspace has
no job title and should not have to invent one. It is required at
the point it means something: accepting an invitation into
someone else's workspace.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c8d4a1b60f37"
down_revision: Union[str, Sequence[str], None] = "b5f18e2ac904"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("job_title", sa.String(length=80), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "job_title")
