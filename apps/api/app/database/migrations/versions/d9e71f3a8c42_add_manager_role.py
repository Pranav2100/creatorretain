"""add a Manager role between Admin and Member

Revision ID: d9e71f3a8c42
Revises: c8d4a1b60f37
Create Date: 2026-10-27 06:40:00.000000

The person who runs a creator account and the person who hires
and removes staff are different jobs, and until now they were the
same role. Anyone who needed to review a creator's work had to be
made an Admin, which also handed them the team and the company
page.

Added rather than recreated: the type is in use by two tables, and
ALTER TYPE ... ADD VALUE keeps every existing row where it is.
Nobody's role changes by applying this.

Labels are the Python enum's NAMES, uppercase, because that is
what SQLAlchemy writes - see e2b47f09c1d6 for what happens when
they are not.

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d9e71f3a8c42"
down_revision: Union[str, Sequence[str], None] = "c8d4a1b60f37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    if bind.dialect.name != "postgresql":
        # Other backends render this column as text constrained
        # from the model, so there is no type to extend.
        return

    # Allowed inside a transaction since PostgreSQL 12, provided
    # the new label is not used in the same transaction. Nothing
    # here writes a row, so it is not.
    op.execute(
        "ALTER TYPE workspace_role ADD VALUE IF NOT EXISTS 'MANAGER'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    if bind.dialect.name != "postgresql":
        return

    # PostgreSQL cannot drop one label from an enum type, so going
    # back means rebuilding the type - and deciding what becomes
    # of the people holding the role. They are demoted to Member,
    # the only answer that cannot accidentally grant anybody
    # anything.
    op.execute(
        "UPDATE workspace_members SET role = 'MEMBER' "
        "WHERE role = 'MANAGER'"
    )
    op.execute(
        "UPDATE workspace_invitations SET role = 'MEMBER' "
        "WHERE role = 'MANAGER'"
    )

    op.execute("ALTER TYPE workspace_role RENAME TO workspace_role_old")
    op.execute(
        "CREATE TYPE workspace_role AS ENUM "
        "('OWNER', 'ADMIN', 'MEMBER')"
    )

    for table in ("workspace_members", "workspace_invitations"):
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN role TYPE workspace_role "
            f"USING role::text::workspace_role"
        )

    op.execute("DROP TYPE workspace_role_old")
