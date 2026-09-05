from uuid import UUID

from sqlalchemy import case
from sqlalchemy.orm import Session, joinedload

from app.common.enums import WorkspaceMemberStatus, WorkspaceRole
from app.database.models.workspace_member import WorkspaceMember
from app.database.repositories.base import BaseRepository


class WorkspaceMemberRepository(BaseRepository[WorkspaceMember]):
    def __init__(self, db: Session):
        super().__init__(db, WorkspaceMember)

    def get_by_id(
        self,
        member_id: UUID,
    ) -> WorkspaceMember | None:
        return (
            self.db.query(self.model)
            .filter(
                self.model.id == member_id,
            )
            .first()
        )

    def get_by_workspace_and_user(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> WorkspaceMember | None:
        """
        Returns the membership row regardless of status.

        Needed for re-activation, because (workspace_id, user_id)
        is unique and removed members keep their row.
        """
        return (
            self.db.query(self.model)
            .filter(
                self.model.workspace_id == workspace_id,
                self.model.user_id == user_id,
            )
            .first()
        )

    def get_active_by_workspace_and_user(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> WorkspaceMember | None:
        return (
            self.db.query(self.model)
            .filter(
                self.model.workspace_id == workspace_id,
                self.model.user_id == user_id,
                self.model.status == WorkspaceMemberStatus.ACTIVE,
                self.model.deleted_at.is_(None),
            )
            .first()
        )

    def get_active_membership(
        self,
        user_id: UUID,
    ) -> WorkspaceMember | None:
        """
        A user may belong to at most one workspace at a time,
        so this resolves the workspace the user is acting in.
        """
        return (
            self.db.query(self.model)
            .filter(
                self.model.user_id == user_id,
                self.model.status == WorkspaceMemberStatus.ACTIVE,
                self.model.deleted_at.is_(None),
            )
            .first()
        )

    def get_active_membership_by_user(
        self,
        user_id: UUID,
    ) -> WorkspaceMember | None:
        return self.get_active_membership(user_id)

    def get_by_workspace(
        self,
        workspace_id: UUID,
    ) -> list[WorkspaceMember]:
        # Explicit ordering: enum sort order differs between a native
        # PostgreSQL enum and the VARCHAR fallback used elsewhere.
        role_order = case(
            (self.model.role == WorkspaceRole.OWNER, 0),
            (self.model.role == WorkspaceRole.ADMIN, 1),
            else_=2,
        )

        return (
            self.db.query(self.model)
            .options(joinedload(self.model.user))
            .filter(
                self.model.workspace_id == workspace_id,
                self.model.status == WorkspaceMemberStatus.ACTIVE,
                self.model.deleted_at.is_(None),
            )
            .order_by(
                role_order.asc(),
                self.model.created_at.asc(),
            )
            .all()
        )

    def get_owner(
        self,
        workspace_id: UUID,
    ) -> WorkspaceMember | None:
        return (
            self.db.query(self.model)
            .filter(
                self.model.workspace_id == workspace_id,
                self.model.role == WorkspaceRole.OWNER,
                self.model.status == WorkspaceMemberStatus.ACTIVE,
                self.model.deleted_at.is_(None),
            )
            .first()
        )

    def count_active(
        self,
        workspace_id: UUID,
    ) -> int:
        return (
            self.db.query(self.model)
            .filter(
                self.model.workspace_id == workspace_id,
                self.model.status == WorkspaceMemberStatus.ACTIVE,
                self.model.deleted_at.is_(None),
            )
            .count()
        )

    def create_member(
        self,
        member: WorkspaceMember,
    ) -> WorkspaceMember:
        return self.create(member)
