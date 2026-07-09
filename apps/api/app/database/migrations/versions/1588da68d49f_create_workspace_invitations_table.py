"""create workspace invitations table

Revision ID: 1588da68d49f
Revises: 152e99669e4a
Create Date: 2026-07-09 19:59:00.468718

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1588da68d49f"
down_revision: Union[str, Sequence[str], None] = "152e99669e4a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "workspace_invitations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("invited_by", sa.UUID(), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(
                "OWNER",
                "ADMIN",
                "MEMBER",
                name="workspace_role",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING",
                "ACCEPTED",
                "DECLINED",
                "EXPIRED",
                "CANCELLED",
                name="workspace_invitation_status",
            ),
            nullable=False,
        ),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
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
            ["invited_by"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "email",
            "status",
            name="uq_workspace_invitation_workspace_email_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )

    op.create_index(
        op.f("ix_workspace_invitations_deleted_at"),
        "workspace_invitations",
        ["deleted_at"],
        unique=False,
    )

    op.create_index(
        op.f("ix_workspace_invitations_email"),
        "workspace_invitations",
        ["email"],
        unique=False,
    )

    op.create_index(
        op.f("ix_workspace_invitations_user_id"),
        "workspace_invitations",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_workspace_invitations_workspace_id"),
        "workspace_invitations",
        ["workspace_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        op.f("ix_workspace_invitations_workspace_id"),
        table_name="workspace_invitations",
    )

    op.drop_index(
        op.f("ix_workspace_invitations_user_id"),
        table_name="workspace_invitations",
    )

    op.drop_index(
        op.f("ix_workspace_invitations_email"),
        table_name="workspace_invitations",
    )

    op.drop_index(
        op.f("ix_workspace_invitations_deleted_at"),
        table_name="workspace_invitations",
    )

    op.drop_table("workspace_invitations")