from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.mixins.timestamps import TimestampMixin
from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.user import User
    from app.database.models.workspace import Workspace


class WorkspaceBlock(Base, TimestampMixin):
    """
    One workspace refusing to hear from another.

    The price of letting anyone write to anyone. A creator whose
    profile is public will eventually be pitched by somebody they
    want nothing from, and the honest answer to that is a way to
    stop it rather than a promise that it will not happen.

    One-directional and silent. The blocked side is told their
    message could not be delivered, not that they have been
    blocked - saying so turns a quiet exit into an argument, and
    the point was to end the conversation.
    """

    __tablename__ = "workspace_blocks"

    __table_args__ = (
        UniqueConstraint(
            "blocker_workspace_id",
            "blocked_workspace_id",
            name="uq_workspace_block",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    blocker_workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    blocked_workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    blocked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Kept for whoever has to look at a report later. Never shown
    # to the blocked side.
    reason: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )

    blocker: Mapped["Workspace"] = relationship(
        "Workspace",
        foreign_keys=[blocker_workspace_id],
    )

    blocked: Mapped["Workspace"] = relationship(
        "Workspace",
        foreign_keys=[blocked_workspace_id],
    )

    def __repr__(self) -> str:
        return (
            f"<WorkspaceBlock {self.blocker_workspace_id} "
            f"blocks {self.blocked_workspace_id}>"
        )
