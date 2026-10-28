"""keep a history of everything that happens to a retainer

Revision ID: a7c3d019f4be
Revises: e2b47f09c1d6
Create Date: 2026-10-22 02:10:00.000000

Append-only, which is why there is no updated_at: a row nothing
updates needs no column saying when it last was, and leaving one
there invites something to start writing it.

The labels are the Python enum's NAMES, uppercase, because that is
what SQLAlchemy writes - the thing that went wrong one migration
ago. verify_migrations.py checks this file against the model
without needing a database.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a7c3d019f4be"
down_revision: Union[str, Sequence[str], None] = "e2b47f09c1d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # Spelled out rather than built from a constant, because a
    # migration is a historical record and has to be readable on
    # its own - and because the checker reads these files as text
    # and cannot follow a name it would have to evaluate.
    if bind.dialect.name == "postgresql":
        kind = postgresql.ENUM(
            "OFFERED",
            "ACCEPTED",
            "DECLINED",
            "OFFER_WITHDRAWN",
            "PAUSE_REQUESTED",
            "RESUME_REQUESTED",
            "REQUEST_REJECTED",
            "REQUEST_WITHDRAWN",
            "PAUSED",
            "RESUMED",
            "NOTICE_GIVEN",
            "ENDED",
            "WORK_SUBMITTED",
            "WORK_APPROVED",
            "CHANGES_REQUESTED",
            "WORK_REJECTED",
            name="retainer_event_kind",
            create_type=False,
        )
        kind.create(bind, checkfirst=True)
    else:
        kind = sa.Enum(
            "OFFERED",
            "ACCEPTED",
            "DECLINED",
            "OFFER_WITHDRAWN",
            "PAUSE_REQUESTED",
            "RESUME_REQUESTED",
            "REQUEST_REJECTED",
            "REQUEST_WITHDRAWN",
            "PAUSED",
            "RESUMED",
            "NOTICE_GIVEN",
            "ENDED",
            "WORK_SUBMITTED",
            "WORK_APPROVED",
            "CHANGES_REQUESTED",
            "WORK_REJECTED",
            name="retainer_event_kind",
        )

    op.create_table(
        "retainer_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "retainer_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("kind", kind, nullable=False),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("actor_name", sa.String(length=120), nullable=True),
        sa.Column("actor_side", sa.String(length=10), nullable=True),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.Column("subject", sa.String(length=120), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["retainer_id"],
            ["retainers.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # One retainer's history in date order is the only read this
    # table has, and the pulse endpoint runs it every few seconds
    # per open tab, so the pair is indexed together.
    op.create_index(
        "ix_retainer_events_retainer_id",
        "retainer_events",
        ["retainer_id"],
    )
    op.create_index(
        "ix_retainer_events_created_at",
        "retainer_events",
        ["created_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_retainer_events_created_at",
        table_name="retainer_events",
    )
    op.drop_index(
        "ix_retainer_events_retainer_id",
        table_name="retainer_events",
    )
    op.drop_table("retainer_events")

    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS retainer_event_kind")
