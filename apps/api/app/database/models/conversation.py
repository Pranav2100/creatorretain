from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.mixins.timestamps import TimestampMixin
from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.message import Message
    from app.database.models.user import User
    from app.database.models.workspace import Workspace


class Conversation(Base, TimestampMixin):
    """
    One thread between two workspaces.

    Between workspaces rather than between people, because the
    agency side turns over: the manager who opened the
    conversation leaves, somebody else picks the account up, and
    the thread has to come with it. Tying it to two people would
    mean a creator losing their history every time an agency
    reshuffles.

    The pair is stored in a fixed order - lower id first - so the
    unique constraint actually prevents a second thread between
    the same two. Without that ordering, A-to-B and B-to-A are
    different rows and two people end up talking past each other
    in separate threads.
    """

    __tablename__ = "conversations"

    __table_args__ = (
        UniqueConstraint(
            "lower_workspace_id",
            "higher_workspace_id",
            name="uq_conversation_pair",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Named for their place in the ordering rather than for any
    # role, because which of the two hires the other is not this
    # table's business and can change.
    lower_workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    higher_workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    started_by_workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Whoever opened it keeps sight of it even without being
    # assigned to the creator, which is the only way a manager
    # can start a conversation about somebody nobody has hired
    # yet and still find it afterwards.
    started_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # When the side that did not start it let it in.
    #
    # Null means it is still a request: it sits in the recipient's
    # requests rather than their inbox, and the sender is rationed
    # until it is answered. Replying sets this, because replying
    # to somebody is the clearest possible way of accepting them.
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # When it was turned away. The thread stops existing for the
    # recipient and the sender cannot add to it, but the row stays
    # so the same stranger cannot simply start again - and so a
    # change of mind is possible without losing what was said.
    declined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Denormalised so an inbox can be ordered and previewed
    # without reaching into the messages of every thread.
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    message_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    lower_workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        foreign_keys=[lower_workspace_id],
    )

    higher_workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        foreign_keys=[higher_workspace_id],
    )

    started_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[started_by_user_id],
    )

    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    @staticmethod
    def order_pair(
        one: uuid.UUID,
        other: uuid.UUID,
    ) -> tuple[uuid.UUID, uuid.UUID]:
        """
        The two ids in the order this table stores them.

        Every read and write of a pair goes through here, so
        there is one answer to "which way round" rather than one
        per caller.
        """
        return (one, other) if str(one) < str(other) else (other, one)

    def other_than(self, workspace_id: uuid.UUID) -> uuid.UUID:
        """The workspace at the far end, from one end's point of view."""
        if workspace_id == self.lower_workspace_id:
            return self.higher_workspace_id

        return self.lower_workspace_id

    def includes(self, workspace_id: uuid.UUID) -> bool:
        return workspace_id in (
            self.lower_workspace_id,
            self.higher_workspace_id,
        )

    def is_request_for(self, workspace_id: uuid.UUID) -> bool:
        """
        Whether this is still somebody asking to be let in.

        Only ever true for the side that did not start it. The
        sender does not see their own message as a request - from
        where they sit they have written to somebody, which is
        exactly what they did.
        """
        return (
            self.accepted_at is None
            and self.declined_at is None
            and self.started_by_workspace_id != workspace_id
        )

    def is_open(self) -> bool:
        """Whether anything more can be said in it."""
        return self.declined_at is None

    def __repr__(self) -> str:
        return (
            f"<Conversation {self.lower_workspace_id} "
            f"{self.higher_workspace_id}>"
        )
