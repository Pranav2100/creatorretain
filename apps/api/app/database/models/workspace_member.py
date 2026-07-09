from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import (
    WorkspaceMemberStatus,
    WorkspaceRole,
)
from app.database.mixins.timestamps import TimestampMixin
from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.user import User
    from app.database.models.workspace import Workspace


class WorkspaceMember(Base, TimestampMixin):
    __tablename__ = "workspace_members"

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

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[WorkspaceRole] = mapped_column(
        Enum(
            WorkspaceRole,
            name="workspace_role",
        ),
        nullable=False,
    )

    status: Mapped[WorkspaceMemberStatus] = mapped_column(
        Enum(
            WorkspaceMemberStatus,
            name="workspace_member_status",
        ),
        default=WorkspaceMemberStatus.ACTIVE,
        nullable=False,
    )

    workspace: Mapped["Workspace"] = relationship()

    user: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return (
            f"<WorkspaceMember "
            f"{self.workspace_id}:{self.user_id}>"
        )