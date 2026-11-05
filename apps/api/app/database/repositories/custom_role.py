from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.database.models.workspace_custom_role import (
    WorkspaceCustomRole,
)
from app.database.models.workspace_member import WorkspaceMember
from app.database.models.workspace_member_role import (
    WorkspaceMemberRole,
)
from app.database.repositories.base import BaseRepository


class CustomRoleRepository(BaseRepository[WorkspaceCustomRole]):
    """
    Reading and writing a workspace's own roles, and who holds
    them.

    Grants are soft-deleted, so every query for a live grant says
    `deleted_at.is_(None)`. Roles themselves are not: a role is
    configuration a workspace wrote, not a record of something
    that happened, and keeping a deleted one around would hold
    its name hostage against the unique constraint for ever.
    """

    def __init__(self, db: Session):
        super().__init__(db, WorkspaceCustomRole)

    # ------------------------------------------------------------------
    # Roles
    # ------------------------------------------------------------------

    def list_for_workspace(
        self,
        workspace_id: UUID,
    ) -> list[WorkspaceCustomRole]:
        return (
            self.db.query(WorkspaceCustomRole)
            .filter(WorkspaceCustomRole.workspace_id == workspace_id)
            # Name breaks ties so the order is stable. Two roles
            # sharing a position otherwise come back in whatever
            # order the database felt like, which makes a list
            # that reshuffles itself between page loads.
            .order_by(
                WorkspaceCustomRole.position.asc(),
                WorkspaceCustomRole.name.asc(),
            )
            .all()
        )

    def get(
        self,
        workspace_id: UUID,
        role_id: UUID,
    ) -> WorkspaceCustomRole | None:
        return (
            self.db.query(WorkspaceCustomRole)
            .filter(
                WorkspaceCustomRole.id == role_id,
                # Scoped to the workspace on the way in, so a role
                # id from somewhere else reads as missing rather
                # than as forbidden.
                WorkspaceCustomRole.workspace_id == workspace_id,
            )
            .first()
        )

    def get_by_name(
        self,
        workspace_id: UUID,
        name: str,
    ) -> WorkspaceCustomRole | None:
        return (
            self.db.query(WorkspaceCustomRole)
            .filter(
                WorkspaceCustomRole.workspace_id == workspace_id,
                # Case-insensitive: "Editor" and "editor" in one
                # list are a mistake, not two roles.
                WorkspaceCustomRole.name.ilike(name),
            )
            .first()
        )

    def count_for_workspace(self, workspace_id: UUID) -> int:
        return (
            self.db.query(WorkspaceCustomRole)
            .filter(WorkspaceCustomRole.workspace_id == workspace_id)
            .count()
        )

    def next_position(self, workspace_id: UUID) -> int:
        last = (
            self.db.query(WorkspaceCustomRole)
            .filter(WorkspaceCustomRole.workspace_id == workspace_id)
            .order_by(WorkspaceCustomRole.position.desc())
            .first()
        )

        return 0 if last is None else last.position + 1

    def create(
        self,
        workspace_id: UUID,
        name: str,
        permissions: list[str],
        created_by_user_id: UUID | None,
    ) -> WorkspaceCustomRole:
        role = WorkspaceCustomRole(
            workspace_id=workspace_id,
            name=name,
            permissions=permissions,
            position=self.next_position(workspace_id),
            created_by_user_id=created_by_user_id,
        )

        self.db.add(role)
        self.db.flush()

        return role

    def delete(self, role: WorkspaceCustomRole) -> None:
        # Grants go with it, by the cascade on the foreign key.
        self.db.delete(role)
        self.db.flush()

    # ------------------------------------------------------------------
    # Who holds what
    # ------------------------------------------------------------------

    def roles_for_member(
        self,
        member_id: UUID,
    ) -> list[WorkspaceCustomRole]:
        rows = (
            self.db.query(WorkspaceMemberRole)
            .options(joinedload(WorkspaceMemberRole.custom_role))
            .filter(
                WorkspaceMemberRole.member_id == member_id,
                WorkspaceMemberRole.deleted_at.is_(None),
            )
            .all()
        )

        return [row.custom_role for row in rows if row.custom_role]

    def roles_by_user(
        self,
        workspace_id: UUID,
    ) -> dict[UUID, list[WorkspaceCustomRole]]:
        """
        Every live grant in the workspace, in one query.

        The Team list needs each person's roles beside their name,
        and asking per person turns one page into one query per
        member.

        Keyed by user rather than by membership row, because that
        is what a page listing people has to hand.
        """
        rows = (
            self.db.query(WorkspaceMemberRole)
            .join(
                WorkspaceMember,
                WorkspaceMember.id == WorkspaceMemberRole.member_id,
            )
            # The member as well as the role: the join above is
            # only a filter, so reading row.member.user_id below
            # would otherwise fetch each one separately and turn
            # this back into a query per person.
            .options(
                joinedload(WorkspaceMemberRole.custom_role),
                joinedload(WorkspaceMemberRole.member),
            )
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMemberRole.deleted_at.is_(None),
            )
            .all()
        )

        out: dict[UUID, list[WorkspaceCustomRole]] = {}

        for row in rows:
            if row.custom_role is None:
                continue
            out.setdefault(row.member.user_id, []).append(
                row.custom_role
            )

        for roles in out.values():
            roles.sort(key=lambda r: (r.position, r.name))

        return out

    def get_grant(
        self,
        member_id: UUID,
        role_id: UUID,
        include_revoked: bool = False,
    ) -> WorkspaceMemberRole | None:
        query = self.db.query(WorkspaceMemberRole).filter(
            WorkspaceMemberRole.member_id == member_id,
            WorkspaceMemberRole.custom_role_id == role_id,
        )

        if not include_revoked:
            query = query.filter(
                WorkspaceMemberRole.deleted_at.is_(None),
            )

        return query.first()

    def record_grant(
        self,
        member_id: UUID,
        role_id: UUID,
        granted_by_user_id: UUID | None,
    ) -> WorkspaceMemberRole:
        # Reuses a revoked row rather than inserting beside it,
        # because the unique constraint covers revoked rows too.
        existing = self.get_grant(
            member_id,
            role_id,
            include_revoked=True,
        )

        if existing is not None:
            existing.deleted_at = None
            existing.granted_by_user_id = granted_by_user_id
            self.db.flush()
            return existing

        grant = WorkspaceMemberRole(
            member_id=member_id,
            custom_role_id=role_id,
            granted_by_user_id=granted_by_user_id,
        )

        self.db.add(grant)
        self.db.flush()

        return grant

    def revoke(self, grant: WorkspaceMemberRole) -> None:
        grant.deleted_at = datetime.now(UTC)
        self.db.flush()

    def holder_count(self, role_id: UUID) -> int:
        return (
            self.db.query(WorkspaceMemberRole)
            .filter(
                WorkspaceMemberRole.custom_role_id == role_id,
                WorkspaceMemberRole.deleted_at.is_(None),
            )
            .count()
        )
