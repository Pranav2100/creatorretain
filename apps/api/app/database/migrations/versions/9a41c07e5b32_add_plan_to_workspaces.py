"""add plan to workspaces

Revision ID: 9a41c07e5b32
Revises: 7d2c95b1e4af
Create Date: 2026-09-29 18:40:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9a41c07e5b32"
down_revision: Union[str, Sequence[str], None] = "7d2c95b1e4af"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    plan = postgresql.ENUM(
        "FREE",
        "PRO",
        "BUSINESS",
        "MANAGED",
        "VERIFIED",
        name="workspace_plan",
        create_type=False,
    )
    plan.create(bind, checkfirst=True)

    op.add_column(
        "workspaces",
        sa.Column(
            "plan",
            plan,
            server_default="FREE",
            nullable=False,
        ),
    )

    op.add_column(
        "workspaces",
        sa.Column(
            "plan_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_workspaces_plan",
        "workspaces",
        ["plan"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_workspaces_plan", table_name="workspaces")
    op.drop_column("workspaces", "plan_expires_at")
    op.drop_column("workspaces", "plan")

    sa.Enum(name="workspace_plan").drop(
        op.get_bind(),
        checkfirst=True,
    )
