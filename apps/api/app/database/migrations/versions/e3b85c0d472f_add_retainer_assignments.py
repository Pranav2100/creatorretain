"""record who runs which retainer

Revision ID: e3b85c0d472f
Revises: d9e71f3a8c42
Create Date: 2026-10-27 06:55:00.000000

A table rather than a column on the retainer, because an account
is often two people and a single owner column makes a handover
look like a replacement.

This is also what a Manager's view is narrowed by, so the pair is
indexed both ways round: by retainer, to show who is on one, and
by user, to list what is theirs.

Empty to begin with, which means every Manager sees nothing until
somebody assigns them. That is the safe direction for a change
about who can see what - nobody gains sight of anything by
applying this.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e3b85c0d472f"
down_revision: Union[str, Sequence[str], None] = "d9e71f3a8c42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "retainer_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "retainer_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "assigned_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["retainer_id"], ["retainers.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "retainer_id", "user_id", name="uq_retainer_assignment"
        ),
    )

    op.create_index(
        "ix_retainer_assignments_retainer_id",
        "retainer_assignments",
        ["retainer_id"],
    )
    op.create_index(
        "ix_retainer_assignments_user_id",
        "retainer_assignments",
        ["user_id"],
    )
    op.create_index(
        "ix_retainer_assignments_deleted_at",
        "retainer_assignments",
        ["deleted_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_retainer_assignments_deleted_at",
        table_name="retainer_assignments",
    )
    op.drop_index(
        "ix_retainer_assignments_user_id",
        table_name="retainer_assignments",
    )
    op.drop_index(
        "ix_retainer_assignments_retainer_id",
        table_name="retainer_assignments",
    )
    op.drop_table("retainer_assignments")
