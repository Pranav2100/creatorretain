"""create retainer tables

Revision ID: b2e7c91d84af
Revises: 9a41c07e5b32
Create Date: 2026-10-12 02:40:00.000000

Four tables:

  retainers                   the agreement - the rule, written once
  retainer_deliverable_specs  what is owed each month, as a rule
  retainer_periods            the months, created as time passes
  retainer_deliverables       one row per unit of work

deliverable_type already exists in Postgres - creator_rates created
it - so it is referenced with create_type=False rather than being
declared a second time.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b2e7c91d84af"
down_revision: Union[str, Sequence[str], None] = "9a41c07e5b32"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TIMESTAMPS = (
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
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    retainer_status = postgresql.ENUM(
        "PENDING",
        "ACTIVE",
        "PAUSED",
        "DECLINED",
        "CANCELLED",
        "ENDED",
        name="retainer_status",
        create_type=False,
    )
    retainer_status.create(bind, checkfirst=True)

    deliverable_status = postgresql.ENUM(
        "PENDING",
        "SUBMITTED",
        "REVISION_REQUESTED",
        "APPROVED",
        "REJECTED",
        name="deliverable_status",
        create_type=False,
    )
    deliverable_status.create(bind, checkfirst=True)

    # Already created alongside creator_rates. Referenced, not made.
    deliverable_type = postgresql.ENUM(
        "REEL",
        "POST",
        "STORY",
        "VIDEO",
        "UGC",
        "EDITING",
        "STRATEGY",
        name="deliverable_type",
        create_type=False,
    )
    deliverable_type.create(bind, checkfirst=True)

    # ------------------------------------------------------------------
    # retainers
    # ------------------------------------------------------------------

    op.create_table(
        "retainers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "brand_workspace_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "creator_workspace_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column(
            "status",
            retainer_status,
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column(
            "monthly_amount",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default="INR",
            nullable=False,
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "notice_period_days",
            sa.SmallInteger(),
            server_default="30",
            nullable=False,
        ),
        sa.Column(
            "sequence_offset",
            sa.SmallInteger(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "responded_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "paused_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "ended_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "ended_reason",
            sa.String(length=300),
            nullable=True,
        ),
        *TIMESTAMPS,
        sa.ForeignKeyConstraint(
            ["brand_workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["creator_workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_retainers_brand_workspace_id",
        "retainers",
        ["brand_workspace_id"],
    )
    op.create_index(
        "ix_retainers_creator_workspace_id",
        "retainers",
        ["creator_workspace_id"],
    )
    op.create_index("ix_retainers_status", "retainers", ["status"])
    op.create_index(
        "ix_retainers_deleted_at",
        "retainers",
        ["deleted_at"],
    )

    # Counting a workspace's live retainers against its plan is the
    # hottest query in the module, so it gets its own index.
    op.create_index(
        "ix_retainers_brand_status",
        "retainers",
        ["brand_workspace_id", "status"],
    )

    # ------------------------------------------------------------------
    # retainer_deliverable_specs
    # ------------------------------------------------------------------

    op.create_table(
        "retainer_deliverable_specs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "retainer_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "deliverable_type",
            deliverable_type,
            nullable=False,
        ),
        sa.Column(
            "quantity",
            sa.SmallInteger(),
            server_default="1",
            nullable=False,
        ),
        sa.Column("notes", sa.String(length=300), nullable=True),
        *TIMESTAMPS,
        sa.ForeignKeyConstraint(
            ["retainer_id"],
            ["retainers.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_retainer_deliverable_specs_retainer_id",
        "retainer_deliverable_specs",
        ["retainer_id"],
    )
    op.create_index(
        "ix_retainer_deliverable_specs_deleted_at",
        "retainer_deliverable_specs",
        ["deleted_at"],
    )

    # ------------------------------------------------------------------
    # retainer_periods
    # ------------------------------------------------------------------

    op.create_table(
        "retainer_periods",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "retainer_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("sequence", sa.SmallInteger(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column(
            "amount",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default="INR",
            nullable=False,
        ),
        *TIMESTAMPS,
        sa.ForeignKeyConstraint(
            ["retainer_id"],
            ["retainers.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        # The guard that makes period creation safe to repeat: two
        # callers racing to create month 3 cannot both win.
        sa.UniqueConstraint(
            "retainer_id",
            "sequence",
            name="uq_retainer_period_sequence",
        ),
    )

    op.create_index(
        "ix_retainer_periods_retainer_id",
        "retainer_periods",
        ["retainer_id"],
    )
    op.create_index(
        "ix_retainer_periods_period_start",
        "retainer_periods",
        ["period_start"],
    )
    op.create_index(
        "ix_retainer_periods_deleted_at",
        "retainer_periods",
        ["deleted_at"],
    )

    # ------------------------------------------------------------------
    # retainer_deliverables
    # ------------------------------------------------------------------

    op.create_table(
        "retainer_deliverables",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "period_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "deliverable_type",
            deliverable_type,
            nullable=False,
        ),
        sa.Column(
            "position",
            sa.SmallInteger(),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "status",
            deliverable_status,
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column(
            "submitted_url",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column("submitted_note", sa.Text(), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "submission_count",
            sa.SmallInteger(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "reviewed_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("review_note", sa.Text(), nullable=True),
        *TIMESTAMPS,
        sa.ForeignKeyConstraint(
            ["period_id"],
            ["retainer_periods.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_retainer_deliverables_period_id",
        "retainer_deliverables",
        ["period_id"],
    )
    op.create_index(
        "ix_retainer_deliverables_status",
        "retainer_deliverables",
        ["status"],
    )
    op.create_index(
        "ix_retainer_deliverables_deleted_at",
        "retainer_deliverables",
        ["deleted_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("retainer_deliverables")
    op.drop_table("retainer_periods")
    op.drop_table("retainer_deliverable_specs")
    op.drop_table("retainers")

    bind = op.get_bind()

    # deliverable_type is left alone: creator_rates still uses it.
    postgresql.ENUM(name="deliverable_status").drop(
        bind,
        checkfirst=True,
    )
    postgresql.ENUM(name="retainer_status").drop(
        bind,
        checkfirst=True,
    )
