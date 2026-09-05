from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, ConfigDict

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

class SentInvitationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: WorkspaceRole
    status: WorkspaceInvitationStatus
    invited_by: UUID
    created_at: datetime
    expires_at: datetime


class SentInvitationListResponse(BaseModel):
    invitations: list[SentInvitationItem]