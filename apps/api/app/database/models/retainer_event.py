from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import RetainerEventKind
from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.retainer import Retainer
    from app.database.models.user import User


class RetainerEvent(Base):
    """
    One line of a retainer's history.

    Append-only on purpose, which is why it does not take the
    timestamp mixin: a row with an updated_at invites something to
    update it, and a history that can be edited after the fact is
    not a history. Nothing in the service writes to one of these
    twice.

    The actor is stored twice over - the person and the side -
    because they answer different questions. "Saloni asked for
    this" is what a reader wants; "the agency asked for this" is
    what the rules turn on, and it has to survive Saloni leaving
    the workspace.
    """

    __tablename__ = "retainer_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    retainer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retainers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    kind: Mapped[RetainerEventKind] = mapped_column(
        Enum(RetainerEventKind, name="retainer_event_kind"),
        nullable=False,
    )

    # Null for anything time did rather than a person - a retainer
    # that reaches the end of its notice has no actor.
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # The name as it was on the day. A display name read live
    # would quietly rewrite history every time someone renames
    # their workspace, and "Nina Cooks paused this" becoming
    # "Nina Media paused this" six months later is a small lie.
    actor_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    actor_side: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    # Whatever the person typed: a reason for pausing, a note on a
    # review. Kept verbatim rather than folded into the sentence,
    # so the page can show it as a quotation.
    note: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    # What it was about, when it was about one thing: "Reel #2".
    subject: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    retainer: Mapped["Retainer"] = relationship(
        "Retainer",
        back_populates="events",
    )

    actor: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[actor_user_id],
    )

    def __repr__(self) -> str:
        return f"<RetainerEvent {self.kind.value} {self.created_at}>"
