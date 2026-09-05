from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import (
    WorkspaceInvitationStatus,
    WorkspaceRole,
)
from app.database.mixins.timestamps import TimestampMixin
from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.user import User
    from app.database.models.workspace import Workspace


class WorkspaceInvitation(Base, TimestampMixin):
    __tablename__ = "workspace_invitations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    invited_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    role: Mapped[WorkspaceRole] = mapped_column(
        Enum(
            WorkspaceRole,
            name="workspace_role",
        ),
        nullable=False,
    )

    status: Mapped[WorkspaceInvitationStatus] = mapped_column(
        Enum(
            WorkspaceInvitationStatus,
            name="workspace_invitation_status",
        ),
        default=WorkspaceInvitationStatus.PENDING,
        nullable=False,
    )

    token: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    resend_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    workspace: Mapped["Workspace"] = relationship()

    user: Mapped["User"] = relationship(
        foreign_keys=[user_id],
    )

    inviter: Mapped["User"] = relationship(
        foreign_keys=[invited_by],
    )

    @property
    def is_expired(self) -> bool:
        return self.expires_at < datetime.now(UTC)

    @property
    def effective_status(self) -> WorkspaceInvitationStatus:
        """
        A pending invitation past its expiry reads as expired,
        even before anything writes the new status to the row.
        """
        if (
            self.status == WorkspaceInvitationStatus.PENDING
            and self.is_expired
        ):
            return WorkspaceInvitationStatus.EXPIRED

        return self.status

    def __repr__(self) -> str:
        return (
            f"<WorkspaceInvitation "
            f"{self.email}>"
        )