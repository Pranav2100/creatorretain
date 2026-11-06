"""subscriptions, and the webhooks that drive them

Revision ID: c5a92f7b31d8
Revises: b8e3d16f904c
Create Date: 2026-11-07 00:40:00.000000

Two tables and one new enum type.

Neither table is where the application reads whether a workspace
is paid for. That still comes from workspaces.plan and
plan_expires_at, which already lapse to Free on their own -
billing's whole job is pushing that date forward as renewals
arrive. The point of keeping it that way is that a provider
being unreachable, or a webhook arriving late, cannot take away
something somebody has already paid for.

billing_events exists because providers retry. Razorpay resends
an event until it gets a 2xx, and a renewal applied twice would
push a paid-until date a month past what was paid for. Every
event id is written down once and refused after that.

The enum labels are UPPERCASE because SQLAlchemy stores the
member NAME. workspace_plan already exists and is reused rather
than recreated.

Nothing is backfilled. No workspace has a subscription until
somebody buys one, so applying this charges nobody anything and
changes no plan.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c5a92f7b31d8"
down_revision: Union[str, Sequence[str], None] = "b8e3d16f904c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # Spelled out rather than built from the enum: a migration is
    # a historical record and has to read on its own, and the
    # checker reads these files as text.
    if bind.dialect.name == "postgresql":
        status = postgresql.ENUM(
            "PENDING",
            "ACTIVE",
            "PAST_DUE",
            "CANCELLING",
            "ENDED",
            name="subscription_status",
            create_type=False,
        )
        status.create(bind, checkfirst=True)

        # Already exists - every workspace has one. Referenced,
        # not recreated.
        plan = postgresql.ENUM(
            "FREE",
            "PRO",
            "BUSINESS",
            "MANAGED",
            "VERIFIED",
            name="workspace_plan",
            create_type=False,
        )
    else:
        status = sa.Enum(
            "PENDING",
            "ACTIVE",
            "PAST_DUE",
            "CANCELLING",
            "ENDED",
            name="subscription_status",
        )
        plan = sa.Enum(
            "FREE",
            "PRO",
            "BUSINESS",
            "MANAGED",
            "VERIFIED",
            name="workspace_plan",
        )

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column(
            "provider_subscription_id",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column("plan", plan, nullable=False),
        sa.Column("status", status, nullable=False),
        sa.Column("amount", sa.Integer(), nullable=True),
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default=sa.text("'INR'"),
            nullable=False,
        ),
        sa.Column(
            "current_period_end",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "cancelled_at",
            sa.DateTime(timezone=True),
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
            "deleted_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        # Two rows for one provider subscription would mean a
        # renewal applied twice.
        sa.UniqueConstraint(
            "provider",
            "provider_subscription_id",
            name="uq_subscription_provider_ref",
        ),
    )

    op.create_index(
        "ix_subscriptions_workspace_id",
        "subscriptions",
        ["workspace_id"],
    )
    op.create_index(
        "ix_subscriptions_provider_subscription_id",
        "subscriptions",
        ["provider_subscription_id"],
    )
    op.create_index(
        "ix_subscriptions_deleted_at",
        "subscriptions",
        ["deleted_at"],
    )

    op.create_table(
        "billing_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("event_id", sa.String(length=160), nullable=False),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column(
            "provider_subscription_id",
            sa.String(length=120),
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
            "deleted_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        # The whole point of the table: an event seen twice is
        # refused the second time.
        sa.UniqueConstraint(
            "provider", "event_id", name="uq_billing_event_ref"
        ),
    )

    op.create_index(
        "ix_billing_events_event_id", "billing_events", ["event_id"]
    )
    op.create_index(
        "ix_billing_events_provider_subscription_id",
        "billing_events",
        ["provider_subscription_id"],
    )
    op.create_index(
        "ix_billing_events_deleted_at",
        "billing_events",
        ["deleted_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    for index in (
        "ix_billing_events_deleted_at",
        "ix_billing_events_provider_subscription_id",
        "ix_billing_events_event_id",
    ):
        op.drop_index(index, table_name="billing_events")

    op.drop_table("billing_events")

    for index in (
        "ix_subscriptions_deleted_at",
        "ix_subscriptions_provider_subscription_id",
        "ix_subscriptions_workspace_id",
    ):
        op.drop_index(index, table_name="subscriptions")

    op.drop_table("subscriptions")

    # Only ours. workspace_plan is still in use by workspaces.
    op.execute("DROP TYPE IF EXISTS subscription_status")
