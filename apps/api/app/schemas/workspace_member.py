from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.common.enums import (
    InvitableWorkspaceRole,
    WorkspaceMemberStatus,
    WorkspaceRole,
)
from app.database.models.workspace_member import WorkspaceMember


class WorkspaceMemberItem(BaseModel):
    id: UUID
    user_id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    role: WorkspaceRole
    status: WorkspaceMemberStatus
    created_at: datetime

    @classmethod
    def from_member(
        cls,
        member: WorkspaceMember,
    ) -> "WorkspaceMemberItem":
        return cls(
            id=member.id,
            user_id=member.user_id,
            first_name=member.user.first_name,
            last_name=member.user.last_name,
            email=member.user.email,
            role=member.role,
            status=member.status,
            created_at=member.created_at,
        )


class WorkspaceMemberListResponse(BaseModel):
    members: list[WorkspaceMemberItem]


class ChangeMemberRoleRequest(BaseModel):
    role: InvitableWorkspaceRole


class WorkspaceMemberResponse(BaseModel):
    message: str
