"""conversations, messages, read marks and blocks

Revision ID: f41d6a9b2e38
Revises: e3b85c0d472f
Create Date: 2026-10-27 08:10:00.000000

Four tables, and the last one is not optional. Anyone may write
to anyone, so somebody will eventually be written to by somebody
they want nothing from, and the answer to that has to exist on
the day the first message can be sent rather than after the
first complaint.

A thread from a stranger starts as a request: accepted_at null
means it sits in the recipient's requests rather than their
inbox, and the sender is rationed until somebody answers.
Replying sets it, because replying to somebody is the clearest
way of accepting them.

The pair on a conversation is stored lower id first and made
unique, which is what stops A-to-B and B-to-A becoming two
threads with half the history in each.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "f41d6a9b2e38"
down_revision: Union[str, Sequence[str], None] = "e3b85c0d472f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _uuid():
    return postgresql.UUID(as_uuid=True)


def _stamps():
    return (
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
    op.create_table(
        "conversations",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("lower_workspace_id", _uuid(), nullable=False),
        sa.Column("higher_workspace_id", _uuid(), nullable=False),
        sa.Column(
            "started_by_workspace_id", _uuid(), nullable=False
        ),
        sa.Column("started_by_user_id", _uuid(), nullable=True),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "declined_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_message_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "message_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        *_stamps(),
        sa.ForeignKeyConstraint(
            ["lower_workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["higher_workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["started_by_workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["started_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "lower_workspace_id",
            "higher_workspace_id",
            name="uq_conversation_pair",
        ),
    )

    op.create_index(
        "ix_conversations_lower", "conversations",
        ["lower_workspace_id"],
    )
    op.create_index(
        "ix_conversations_higher", "conversations",
        ["higher_workspace_id"],
    )
    # An inbox is ordered by this, every time it is opened.
    op.create_index(
        "ix_conversations_last_message_at", "conversations",
        ["last_message_at"],
    )
    op.create_index(
        "ix_conversations_deleted_at", "conversations",
        ["deleted_at"],
    )

    op.create_table(
        "messages",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("conversation_id", _uuid(), nullable=False),
        sa.Column("sender_workspace_id", _uuid(), nullable=False),
        sa.Column("sender_user_id", _uuid(), nullable=True),
        sa.Column("sender_name", sa.String(length=120), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sender_workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sender_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_messages_conversation_id", "messages",
        ["conversation_id"],
    )
    op.create_index(
        "ix_messages_created_at", "messages", ["created_at"]
    )

    op.create_table(
        "conversation_reads",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("conversation_id", _uuid(), nullable=False),
        sa.Column("user_id", _uuid(), nullable=False),
        sa.Column(
            "read_through",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "conversation_id", "user_id",
            name="uq_conversation_read",
        ),
    )

    op.create_index(
        "ix_conversation_reads_conversation_id",
        "conversation_reads", ["conversation_id"],
    )
    op.create_index(
        "ix_conversation_reads_user_id",
        "conversation_reads", ["user_id"],
    )

    op.create_table(
        "workspace_blocks",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("blocker_workspace_id", _uuid(), nullable=False),
        sa.Column("blocked_workspace_id", _uuid(), nullable=False),
        sa.Column("blocked_by_user_id", _uuid(), nullable=True),
        sa.Column("reason", sa.String(length=300), nullable=True),
        *_stamps(),
        sa.ForeignKeyConstraint(
            ["blocker_workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["blocked_workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["blocked_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "blocker_workspace_id",
            "blocked_workspace_id",
            name="uq_workspace_block",
        ),
    )

    op.create_index(
        "ix_workspace_blocks_blocker", "workspace_blocks",
        ["blocker_workspace_id"],
    )
    op.create_index(
        "ix_workspace_blocks_blocked", "workspace_blocks",
        ["blocked_workspace_id"],
    )
    op.create_index(
        "ix_workspace_blocks_deleted_at", "workspace_blocks",
        ["deleted_at"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("workspace_blocks")
    op.drop_table("conversation_reads")
    op.drop_table("messages")
    op.drop_table("conversations")
