from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.conversation import Conversation
    from app.database.models.user import User


class ConversationRead(Base):
    """
    How far one person has read.

    Per person, not per workspace: an agency conversation is read
    by whoever happens to open it, and marking it read for the
    whole company the moment one colleague glances at it is how
    messages get missed.

    A timestamp rather than a pointer at the last message, so a
    message arriving while somebody has the thread open does not
    need this row rewritten to stay correct - the unread count is
    simply everything newer than the mark.
    """

    __tablename__ = "conversation_reads"

    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "user_id",
            name="uq_conversation_read",
        ),
    )

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

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    read_through: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
    )

    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<ConversationRead {self.user_id} {self.read_through}>"
