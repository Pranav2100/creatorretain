from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.common.enums import (
    InvitableWorkspaceRole,
    WorkspaceInvitationStatus,
    WorkspaceRole,
)


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: InvitableWorkspaceRole


class InvitationResponse(BaseModel):
    message: str

class AcceptInvitationResponse(BaseModel):
    message: str

class WorkspaceInvitationItem(BaseModel):
    id: UUID
    workspace_id: UUID
    email: EmailStr
    role: WorkspaceRole
    status: WorkspaceInvitationStatus
    expires_at: datetime

    model_config = {
        "from_attributes": True,
    }


class WorkspaceInvitationListResponse(BaseModel):
    invitations: list[WorkspaceInvitationItem]