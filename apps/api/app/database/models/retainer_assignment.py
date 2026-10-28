from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.mixins.timestamps import TimestampMixin
from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.retainer import Retainer
    from app.database.models.user import User


class RetainerAssignment(Base, TimestampMixin):
    """
    Who runs this account.

    A row per person per retainer rather than one column on the
    retainer, because an account is often two people - the manager
    who talks to the creator and the one covering while she is
    away - and a single owner column forces a handover to look
    like a replacement.

    This decides what a Manager sees as well as who is
    responsible. Seniors see every retainer in the workspace
    regardless; this table is what narrows the view for everyone
    else, which is why removing a row has to be as deliberate as
    adding one.
    """

    __tablename__ = "retainer_assignments"

    __table_args__ = (
        # Assigning the same person twice is not a second
        # assignment, and a list that can repeat someone makes
        # every count of "how many people are on this" wrong.
        UniqueConstraint(
            "retainer_id",
            "user_id",
            name="uq_retainer_assignment",
        ),
    )

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

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Who put them on it. Kept for the same reason the history is
    # kept: "why can she see this?" is a question with an answer.
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    retainer: Mapped["Retainer"] = relationship(
        "Retainer",
        back_populates="assignments",
    )

    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
    )

    def __repr__(self) -> str:
        return f"<RetainerAssignment {self.retainer_id} {self.user_id}>"
