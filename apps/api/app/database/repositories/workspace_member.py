from uuid import UUID

from sqlalchemy.orm import Session

from app.database.models.workspace_member import WorkspaceMember
from app.database.repositories.base import BaseRepository

from app.common.enums import WorkspaceMemberStatus


class WorkspaceMemberRepository(BaseRepository[WorkspaceMember]):
    def __init__(self, db: Session):
        super().__init__(db, WorkspaceMember)

    def get_by_workspace_and_user(
    self,
    workspace_id,
    user_id,
    ):
        
        return (
            self.db.query(self.model)
            .filter(
                self.model.workspace_id == workspace_id,
                self.model.user_id == user_id,
            )
            .first()
        )
    
    def get_active_membership(
        self,
        user_id,
    ):
        return (
            self.db.query(self.model)
            .filter(
                self.model.user_id == user_id,
                self.model.status == WorkspaceMemberStatus.ACTIVE,
            )
            .first()
        )
    
    def get_active_membership_by_user(
    self,
    user_id: UUID,
    ):
        return (
            self.db.query(self.model)
            .filter(
                self.model.user_id == user_id,
                self.model.status == WorkspaceMemberStatus.ACTIVE,
        )
        .first()
    )
    
    def get_by_workspace(
        self,
        workspace_id: UUID,
    ):
        return (
            self.db.query(self.model)
            .filter(
                self.model.workspace_id == workspace_id,
                self.model.status == WorkspaceMemberStatus.ACTIVE,
            )
            .order_by(
                self.model.role.asc(),
                self.model.created_at.asc(),
            )
            .all()
        )
    
    def create_member(
        self,
        member,
    ):
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member
    