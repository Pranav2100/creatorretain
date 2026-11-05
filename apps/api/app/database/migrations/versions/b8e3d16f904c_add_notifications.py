"""an outbox for email, and what people want to hear about

Revision ID: b8e3d16f904c
Revises: a1c74e82b6d3
Create Date: 2026-11-05 17:20:00.000000

One table and three columns.

The table is an outbox: something that happened writes a row in
the same transaction, and a drain sends it afterwards. The point
is that a notification is a consequence, never the thing itself -
accepting an offer must not fail because a mail provider is down,
and must not take four seconds because it is slow.

The columns are switches, defaulted on. Somebody who never finds
the account page should still hear that an offer arrived; silence
until you discover a setting is the worse failure. There is no
switch for security mail, which is why there are three and not
four.

The enum labels are UPPERCASE because that is what SQLAlchemy
writes - it stores the member NAME, not its value. Getting this
wrong on retainer_request cost this project a production 500, so
it is spelled out here: these must match the Python member names
exactly, and verify_migrations checks that they do.

Nothing is backfilled. The outbox starts empty, so applying this
sends nobody anything.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b8e3d16f904c"
down_revision: Union[str, Sequence[str], None] = "a1c74e82b6d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # Spelled out rather than built from the enum, the way every
    # other migration here does it: a migration is a historical
    # record and has to be readable on its own, and the checker
    # reads these files as text and cannot follow a name it would
    # have to evaluate.
    if bind.dialect.name == "postgresql":
        kind = postgresql.ENUM(
            "OFFER_RECEIVED",
            "OFFER_ACCEPTED",
            "OFFER_DECLINED",
            "PAUSE_REQUESTED",
            "RESUME_REQUESTED",
            "REQUEST_REJECTED",
            "PAUSED",
            "RESUMED",
            "NOTICE_GIVEN",
            "ENDED",
            "WORK_SUBMITTED",
            "WORK_APPROVED",
            "CHANGES_REQUESTED",
            "WORK_REJECTED",
            "UNREAD_MESSAGES",
            "MESSAGE_REQUEST",
            "PASSWORD_CHANGED",
            name="notification_kind",
            create_type=False,
        )
        kind.create(bind, checkfirst=True)
    else:
        kind = sa.Enum(
            "OFFER_RECEIVED",
            "OFFER_ACCEPTED",
            "OFFER_DECLINED",
            "PAUSE_REQUESTED",
            "RESUME_REQUESTED",
            "REQUEST_REJECTED",
            "PAUSED",
            "RESUMED",
            "NOTICE_GIVEN",
            "ENDED",
            "WORK_SUBMITTED",
            "WORK_APPROVED",
            "CHANGES_REQUESTED",
            "WORK_REJECTED",
            "UNREAD_MESSAGES",
            "MESSAGE_REQUEST",
            "PASSWORD_CHANGED",
            name="notification_kind",
        )

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("to_email", sa.String(length=320), nullable=False),
        sa.Column("kind", kind, nullable=False),
        sa.Column(
            "payload",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "send_after",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "dedupe_key", sa.String(length=200), nullable=True
        ),
        sa.Column(
            "sent_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "dropped_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "dropped_reason", sa.String(length=120), nullable=True
        ),
        sa.Column(
            "attempts",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
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
        # From the timestamp mixin, like every other table here.
        sa.Column(
            "deleted_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_notifications_user_id", "notifications", ["user_id"]
    )
    op.create_index(
        "ix_notifications_send_after",
        "notifications",
        ["send_after"],
    )
    op.create_index(
        "ix_notifications_sent_at", "notifications", ["sent_at"]
    )
    op.create_index(
        "ix_notifications_dedupe_key",
        "notifications",
        ["dedupe_key"],
    )
    op.create_index(
        "ix_notifications_deleted_at",
        "notifications",
        ["deleted_at"],
    )

    for column in (
        "notify_retainers",
        "notify_messages",
        "notify_work",
    ):
        op.add_column(
            "users",
            sa.Column(
                column,
                sa.Boolean(),
                server_default=sa.text("true"),
                nullable=False,
            ),
        )


def downgrade() -> None:
    """Downgrade schema."""
    for column in (
        "notify_work",
        "notify_messages",
        "notify_retainers",
    ):
        op.drop_column("users", column)

    for index in (
        "ix_notifications_deleted_at",
        "ix_notifications_dedupe_key",
        "ix_notifications_sent_at",
        "ix_notifications_send_after",
        "ix_notifications_user_id",
    ):
        op.drop_index(index, table_name="notifications")

    op.drop_table("notifications")

    postgresql.ENUM(name="notification_kind").drop(
        op.get_bind(), checkfirst=True
    )
