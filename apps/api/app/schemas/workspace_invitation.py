from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.common.enums import (
    InvitableWorkspaceRole,
    WorkspaceInvitationStatus,
    WorkspaceRole,
)
from app.database.models.workspace_invitation import WorkspaceInvitation


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: InvitableWorkspaceRole


class InvitationResponse(BaseModel):
    message: str


class AcceptInvitationResponse(BaseModel):
    message: str


class WorkspaceInvitationItem(BaseModel):
    """
    What the recipient sees. Carries who invited them and to which
    workspace, so an invitation still makes sense months later.
    """

    id: UUID
    workspace_id: UUID
    workspace_name: str | None
    invited_by_name: str | None
    email: EmailStr
    role: WorkspaceRole
    status: WorkspaceInvitationStatus
    can_request_resend: bool
    resend_requested_at: datetime | None
    created_at: datetime
    expires_at: datetime

    @classmethod
    def from_invitation(
        cls,
        invitation: WorkspaceInvitation,
    ) -> "WorkspaceInvitationItem":
        status = invitation.effective_status

        inviter = invitation.inviter
        workspace = invitation.workspace

        return cls(
            id=invitation.id,
            workspace_id=invitation.workspace_id,
            workspace_name=(
                workspace.display_name if workspace else None
            ),
            invited_by_name=(
                f"{inviter.first_name} {inviter.last_name}"
                if inviter
                else None
            ),
            email=invitation.email,
            role=invitation.role,
            status=status,
            can_request_resend=(
                status == WorkspaceInvitationStatus.EXPIRED
                and invitation.resend_requested_at is None
            ),
            resend_requested_at=invitation.resend_requested_at,
            created_at=invitation.created_at,
            expires_at=invitation.expires_at,
        )


class AcceptByTokenRequest(BaseModel):
    token: str


class InvitationPreviewResponse(BaseModel):
    """
    Safe, public view of an invitation link. Deliberately excludes
    the token, ids and anything about the workspace's members.
    """

    workspace_name: str | None
    invited_by_name: str | None
    email: EmailStr
    role: WorkspaceRole
    status: WorkspaceInvitationStatus
    is_expired: bool
    requires_signup: bool
    expires_at: datetime

    @classmethod
    def from_invitation(
        cls,
        invitation: WorkspaceInvitation,
        requires_signup: bool,
    ) -> "InvitationPreviewResponse":
        inviter = invitation.inviter
        workspace = invitation.workspace

        return cls(
            workspace_name=(
                workspace.display_name if workspace else None
            ),
            invited_by_name=(
                f"{inviter.first_name} {inviter.last_name}"
                if inviter
                else None
            ),
            email=invitation.email,
            role=invitation.role,
            status=invitation.effective_status,
            is_expired=invitation.is_expired,
            requires_signup=requires_signup,
            expires_at=invitation.expires_at,
        )


class WorkspaceInvitationListResponse(BaseModel):
    invitations: list[WorkspaceInvitationItem]


class SentInvitationItem(BaseModel):
    """What the workspace sees about invitations it has sent."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: WorkspaceRole
    status: WorkspaceInvitationStatus
    invited_by: UUID
    resend_requested_at: datetime | None
    created_at: datetime
    expires_at: datetime

    @classmethod
    def from_invitation(
        cls,
        invitation: WorkspaceInvitation,
    ) -> "SentInvitationItem":
        return cls(
            id=invitation.id,
            email=invitation.email,
            role=invitation.role,
            status=invitation.effective_status,
            invited_by=invitation.invited_by,
            resend_requested_at=invitation.resend_requested_at,
            created_at=invitation.created_at,
            expires_at=invitation.expires_at,
        )


class SentInvitationListResponse(BaseModel):
    invitations: list[SentInvitationItem]
