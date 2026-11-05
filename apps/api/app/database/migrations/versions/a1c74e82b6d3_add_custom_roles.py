"""roles a workspace invents for itself

Revision ID: a1c74e82b6d3
Revises: f41d6a9b2e38
Create Date: 2026-11-05 11:40:00.000000

Two tables, and no change to workspace_members.

That is the whole shape of the feature: the four built-in roles
stay exactly as they are and keep deciding who outranks whom, and
a custom role only ever adds permissions on top. Nothing here can
take a permission away from anybody, which is why this migration
cannot change what a single existing person is allowed to do.

Permissions are a JSON array of the lowercase permission values
rather than an array of a Postgres enum. Every enum type in this
schema stores member NAMES, because that is what SQLAlchemy
writes, and keeping hand-written migrations in step with that has
already cost this project one production 500. JSON has no labels
to drift from, and the set is checked against the enum before it
is written.

Empty to begin with. No workspace has a custom role until
somebody makes one, so applying this grants nobody anything.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a1c74e82b6d3"
down_revision: Union[str, Sequence[str], None] = "f41d6a9b2e38"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "workspace_custom_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column(
            "position",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "permissions",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
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
        # Present because every table in this schema has it - the
        # timestamp mixin puts it on every model, so leaving it
        # out here makes the migrated table a column short of
        # what the ORM writes.
        #
        # Unused all the same: a role is hard-deleted. Soft
        # deletion would hold the name hostage against the unique
        # constraint for ever, so deleting "Editor" would mean
        # never being able to have an "Editor" again.
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "name",
            name="uq_workspace_custom_role_name",
        ),
    )

    op.create_index(
        "ix_workspace_custom_roles_workspace_id",
        "workspace_custom_roles",
        ["workspace_id"],
    )
    op.create_index(
        "ix_workspace_custom_roles_deleted_at",
        "workspace_custom_roles",
        ["deleted_at"],
    )

    op.create_table(
        "workspace_member_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "member_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "custom_role_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "granted_by_user_id",
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
            ["member_id"],
            ["workspace_members.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["custom_role_id"],
            ["workspace_custom_roles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        # Covers revoked rows as well as live ones, so granting a
        # role back reuses the row and its history rather than
        # writing a second one. A partial index on deleted_at IS
        # NULL would be tighter but is Postgres-only, and the test
        # suites build this table on SQLite.
        sa.UniqueConstraint(
            "member_id",
            "custom_role_id",
            name="uq_workspace_member_role",
        ),
    )

    op.create_index(
        "ix_workspace_member_roles_member_id",
        "workspace_member_roles",
        ["member_id"],
    )
    op.create_index(
        "ix_workspace_member_roles_custom_role_id",
        "workspace_member_roles",
        ["custom_role_id"],
    )
    op.create_index(
        "ix_workspace_member_roles_deleted_at",
        "workspace_member_roles",
        ["deleted_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_workspace_member_roles_deleted_at",
        table_name="workspace_member_roles",
    )
    op.drop_index(
        "ix_workspace_member_roles_custom_role_id",
        table_name="workspace_member_roles",
    )
    op.drop_index(
        "ix_workspace_member_roles_member_id",
        table_name="workspace_member_roles",
    )
    op.drop_table("workspace_member_roles")

    op.drop_index(
        "ix_workspace_custom_roles_deleted_at",
        table_name="workspace_custom_roles",
    )
    op.drop_index(
        "ix_workspace_custom_roles_workspace_id",
        table_name="workspace_custom_roles",
    )
    op.drop_table("workspace_custom_roles")
