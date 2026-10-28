from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.conversation import Conversation
    from app.database.models.user import User
    from app.database.models.workspace import Workspace


# Long enough for a brief, short enough that nobody pastes a
# novel into a chat box and nothing downstream has to cope with
# a megabyte of text in a list view.
MAX_MESSAGE_LENGTH = 4000


class Message(Base):
    """
    One thing somebody said.

    Append-only, like the retainer history and for the same
    reason: a message that can be edited after the fact is not a
    record of what was said. No updated_at, because nothing
    updates one.

    Both the person and their workspace are stored. The person is
    who the reader wants to see - "Mira said" - and the workspace
    is which side of the conversation it came from, which is what
    the rules turn on and what has to survive her leaving.
    """

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sender_workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    sender_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # The name as it read when they sent it, for the same reason
    # the retainer history keeps one: a workspace renaming itself
    # should not rewrite who said what last March.
    sender_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Stamped by the application, not by the database.
    #
    # A read mark is written from Python with microseconds, and
    # this used to be written by the database clock - which
    # truncates to the second on SQLite. Two clocks of different
    # resolutions meant a message sent in the same second as
    # somebody's last read arrived looking older than that read,
    # and was counted as already seen. The server_default stays
    # as a floor for anything inserted outside the ORM.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )

    sender: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[sender_user_id],
    )

    sender_workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        foreign_keys=[sender_workspace_id],
    )

    def __repr__(self) -> str:
        return f"<Message {self.conversation_id} {self.created_at}>"
