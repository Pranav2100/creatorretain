from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.mixins.timestamps import TimestampMixin
from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.user import User
    from app.database.models.workspace_custom_role import (
        WorkspaceCustomRole,
    )
    from app.database.models.workspace_member import WorkspaceMember


class WorkspaceMemberRole(Base, TimestampMixin):
    """
    One person holding one custom role.

    Soft-deleted rather than removed, and who granted it is kept,
    because "why does this person have this" is a question that
    gets asked after something has gone wrong - at which point a
    row that was deleted outright tells nobody anything.

    The uniqueness constraint covers revoked rows too, so granting
    a role back to someone reuses the row instead of writing a
    second one. The alternative - a partial index on deleted_at IS
    NULL - is Postgres-only, and the suites build this table on
    SQLite.
    """

    __tablename__ = "workspace_member_roles"

    __table_args__ = (
        UniqueConstraint(
            "member_id",
            "custom_role_id",
            name="uq_workspace_member_role",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspace_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    custom_role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "workspace_custom_roles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    granted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # deleted_at comes from the timestamp mixin, indexed, and is
    # genuinely used here: revoking a role soft-deletes the row.

    member: Mapped["WorkspaceMember"] = relationship()

    custom_role: Mapped["WorkspaceCustomRole"] = relationship()

    granted_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[granted_by_user_id],
    )

    def __repr__(self) -> str:
        return (
            f"<WorkspaceMemberRole "
            f"{self.member_id}:{self.custom_role_id}>"
        )
