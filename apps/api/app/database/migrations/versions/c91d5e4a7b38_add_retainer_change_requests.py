"""add pending change requests and notice to retainers

Revision ID: c91d5e4a7b38
Revises: a83f1c6de204
Create Date: 2026-10-19 01:30:00.000000

Pausing a retainer stops the months accruing, which stops the
money, so it is no longer one party's to do alone: it becomes a
request the other side answers.

Ending is different. A change that needs permission is a change
the other side can refuse forever, so ending serves the notice
period both parties already agreed to instead. The wind-down date
goes in end_date, which the period builder already respects, so no
job has to run for a retainer to finish on time.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c91d5e4a7b38"
down_revision: Union[str, Sequence[str], None] = "a83f1c6de204"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

REQUEST = sa.Enum("pause", "resume", name="retainer_request")


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    REQUEST.create(bind, checkfirst=True)

    op.add_column(
        "retainers",
        sa.Column("pending_action", REQUEST, nullable=True),
    )
    op.add_column(
        "retainers",
        sa.Column("pending_by_side", sa.String(length=10), nullable=True),
    )
    op.add_column(
        "retainers",
        sa.Column(
            "pending_by_user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "retainers",
        sa.Column(
            "pending_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "retainers",
        sa.Column("pending_reason", sa.String(length=300), nullable=True),
    )
    op.add_column(
        "retainers",
        sa.Column(
            "notice_given_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "retainers",
        sa.Column(
            "notice_given_by_side",
            sa.String(length=10),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_retainers_pending_by_user_id_users",
        "retainers",
        "users",
        ["pending_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_retainers_pending_by_user_id_users",
        "retainers",
        type_="foreignkey",
    )

    for column in (
        "notice_given_by_side",
        "notice_given_at",
        "pending_reason",
        "pending_at",
        "pending_by_user_id",
        "pending_by_side",
        "pending_action",
    ):
        op.drop_column("retainers", column)

    REQUEST.drop(op.get_bind(), checkfirst=True)
