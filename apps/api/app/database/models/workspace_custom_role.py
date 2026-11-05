from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.permissions import WorkspacePermission
from app.database.mixins.timestamps import TimestampMixin
from app.database.models.base import Base

if TYPE_CHECKING:
    from app.database.models.user import User
    from app.database.models.workspace import Workspace


# Long enough to say what the role is for, short enough to sit in
# a list beside a person's name without wrapping.
MAX_ROLE_NAME_LENGTH = 40

# A workspace that needs more than this does not need roles, it
# needs fewer roles. The cap exists so the Settings list stays
# something a person can read rather than scroll.
MAX_ROLES_PER_WORKSPACE = 25


class WorkspaceCustomRole(Base, TimestampMixin):
    """
    A role a workspace invented for itself.

    Not a replacement for the four built-in roles. Everybody still
    holds exactly one of those, and it still decides who outranks
    whom. A custom role only ever *adds* permissions on top, which
    is what makes the whole thing safe to reason about: there is
    no way to express "an Admin, but without X", so no way to
    quietly take something away from someone and leave the role
    name looking unchanged.

    Hard-deleted, unlike almost everything else here. The
    timestamp mixin still puts a deleted_at on the table, and it
    stays NULL: soft-deleting a role would hold its name against
    the unique constraint for ever, so deleting "Editor" would
    mean never being able to have an "Editor" again. Deleting a
    role takes it off everybody who held it, by the cascade.

    `position` orders the list and nothing else. This is the one
    place the design departs from Discord, where a role's height
    is its authority. Here authority comes from the subset rule in
    the permissions module - you can only put into a role what you
    already hold - which does the same job without needing anybody
    to understand an ordering. Dragging a role up the list changes
    where it appears and not what it can do.
    """

    __tablename__ = "workspace_custom_roles"

    __table_args__ = (
        # Two roles with the same name in one workspace would make
        # the Team list a guessing game. Scoped to the workspace,
        # so unrelated agencies can both have an "Editor".
        UniqueConstraint(
            "workspace_id",
            "name",
            name="uq_workspace_custom_role_name",
        ),
    )

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

    name: Mapped[str] = mapped_column(
        String(MAX_ROLE_NAME_LENGTH),
        nullable=False,
    )

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Stored as a JSON array of permission *values* rather than as
    # an array of a Postgres enum.
    #
    # Deliberate, and the reason is scar tissue: a Postgres enum
    # column written by SQLAlchemy stores the member NAME, while
    # every migration in this project writing those types by hand
    # had to be taught to match. That mismatch has already cost
    # this codebase one production 500. JSON has no type to drift
    # from, the values are the lowercase strings the API already
    # speaks, and the set is validated against the enum on the way
    # in - so an unknown permission cannot be stored, whatever a
    # client sends.
    #
    # JSONB on Postgres, plain JSON on SQLite, so the suites can
    # build this table with create_all.
    permissions: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
    )

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    workspace: Mapped["Workspace"] = relationship()

    created_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[created_by_user_id],
    )

    @property
    def granted(self) -> frozenset[WorkspacePermission]:
        """
        What this role actually grants.

        Anything stored that is no longer a permission is dropped
        rather than raising. A permission removed from the enum in
        a later version leaves rows behind that mention it, and a
        workspace should not become unloadable because one of its
        roles names something retired.
        """
        known = {p.value for p in WorkspacePermission}

        return frozenset(
            WorkspacePermission(value)
            for value in (self.permissions or [])
            if value in known
        )

    def __repr__(self) -> str:
        return (
            f"<WorkspaceCustomRole {self.workspace_id}:{self.name}>"
        )
