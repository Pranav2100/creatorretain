"""fix the labels on the retainer_request enum type

Revision ID: e2b47f09c1d6
Revises: c91d5e4a7b38
Create Date: 2026-10-19 02:00:00.000000

SQLAlchemy persists a Python enum by its NAME, not its value, so
every enum type in this database carries uppercase labels -
PENDING, ACTIVE, SUBMITTED. c91d5e4a7b38 created retainer_request
with the lowercase values instead, so PostgreSQL refused every
write to pending_action and asking to pause a retainer answered
with a 500.

Dropping and recreating is safe precisely because nothing could
ever be stored in that column: every row is null.

SQLite never showed this, because the suites build their schema
from the models rather than from these files - which means the
migrations had never been run anywhere except a real PostgreSQL
database. verify_migrations.py now compares the two without
needing one.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e2b47f09c1d6"
down_revision: Union[str, Sequence[str], None] = "c91d5e4a7b38"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    if bind.dialect.name != "postgresql":
        # Other backends render this column as text constrained
        # from the model, so there is no type to correct.
        return

    op.drop_column("retainers", "pending_action")
    op.execute("DROP TYPE IF EXISTS retainer_request")

    kind = postgresql.ENUM(
        "PAUSE",
        "RESUME",
        name="retainer_request",
        create_type=False,
    )
    kind.create(bind, checkfirst=True)

    op.add_column(
        "retainers",
        sa.Column("pending_action", kind, nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    if bind.dialect.name != "postgresql":
        return

    op.drop_column("retainers", "pending_action")
    op.execute("DROP TYPE IF EXISTS retainer_request")

    kind = postgresql.ENUM(
        "pause",
        "resume",
        name="retainer_request",
        create_type=False,
    )
    kind.create(bind, checkfirst=True)

    op.add_column(
        "retainers",
        sa.Column("pending_action", kind, nullable=True),
    )
