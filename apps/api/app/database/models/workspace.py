from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import (
    VerificationStatus,
    WorkspacePlan,
    WorkspaceStatus,
    WorkspaceType,
)
from app.database.mixins.timestamps import TimestampMixin
from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.user import User


class Workspace(Base, TimestampMixin):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    display_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    legal_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    slug: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )

    workspace_type: Mapped[WorkspaceType] = mapped_column(
        Enum(WorkspaceType, name="workspace_type"),
        nullable=False,
    )

    plan: Mapped[WorkspacePlan] = mapped_column(
        Enum(WorkspacePlan, name="workspace_plan"),
        default=WorkspacePlan.FREE,
        nullable=False,
        index=True,
    )

    # When the current plan lapses. Null means it does not - which is
    # every workspace until billing exists. A paid plan past this date
    # reads as Free without anything having to run.
    plan_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status"),
        default=VerificationStatus.NOT_VERIFIED,
        nullable=False,
    )

    status: Mapped[WorkspaceStatus] = mapped_column(
        Enum(WorkspaceStatus, name="workspace_status"),
        default=WorkspaceStatus.ACTIVE,
        nullable=False,
    )

    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    logo_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    banner_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    slug_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    owner: Mapped["User"] = relationship(
        back_populates="owned_workspaces",
    )

    @property
    def effective_plan(self) -> WorkspacePlan:
        """
        The plan actually in force. A lapsed paid plan reads as Free
        the moment it expires, computed rather than swept, the same
        way an expired invitation reads as expired.
        """
        if self.plan == WorkspacePlan.FREE:
            return WorkspacePlan.FREE

        if self.plan_expires_at is None:
            return self.plan

        if self.plan_expires_at > datetime.now(
            self.plan_expires_at.tzinfo,
        ):
            return self.plan

        return WorkspacePlan.FREE

    def __repr__(self) -> str:
        return f"<Workspace {self.slug}>"