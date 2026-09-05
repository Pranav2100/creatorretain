import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID
from app.common.enums import (InvitableWorkspaceRole,WorkspaceInvitationStatus,WorkspaceRole,WorkspaceType,)
from app.database.models.workspace_invitation import WorkspaceInvitation
from app.database.repositories.user import UserRepository
from app.database.repositories.workspace import WorkspaceRepository
from app.database.repositories.workspace_invitation import (WorkspaceInvitationRepository,)
from app.database.repositories.workspace_member import (WorkspaceMemberRepository,)
from app.schemas.workspace_invitation import InviteMemberRequest
from app.common.enums import WorkspaceMemberStatus
from app.database.models.workspace_member import WorkspaceMember


class WorkspaceInvitationService:
    def __init__(
        self,
        workspace_repository: WorkspaceRepository,
        member_repository: WorkspaceMemberRepository,
        invitation_repository: WorkspaceInvitationRepository,
        user_repository: UserRepository,
    ):
        self.workspace_repository = workspace_repository
        self.member_repository = member_repository
        self.invitation_repository = invitation_repository
        self.user_repository = user_repository

    def invite_member(
        self,
        current_user_id: UUID,
        request: InviteMemberRequest,
    ) -> WorkspaceInvitation:

        # Normalize email
        request.email = request.email.lower().strip()

        # Get current user
        current_user = self.user_repository.get_by_id(current_user_id)

        if current_user is None:
            raise ValueError("User not found.")

        # Cannot invite yourself
        if current_user.email.lower() == request.email:
            raise ValueError("You cannot invite yourself.")

        # Get owner's workspace
        workspace = self.workspace_repository.get_by_owner(current_user_id)

        if workspace is None:
            raise ValueError("Workspace not found.")

        # Creators cannot invite members
        if workspace.workspace_type == WorkspaceType.CREATOR:
            raise ValueError(
                "Creator workspaces cannot invite members."
            )

        # Current user's membership
        membership = self.member_repository.get_by_workspace_and_user(
            workspace.id,
            current_user_id,
        )

        if membership is None:
            raise ValueError("Access denied.")

        # Only Owner/Admin can invite
        if membership.role not in (
            WorkspaceRole.OWNER,
            WorkspaceRole.ADMIN,
        ):
            raise ValueError(
                "You don't have permission to invite members."
            )

        # Existing pending invitation
        existing_invitation = (
            self.invitation_repository.get_pending_by_workspace_and_email(
                workspace.id,
                request.email,
            )
        )

        if existing_invitation is not None:
            raise ValueError(
                "An active invitation already exists."
            )

        # Existing registered user
        existing_user = self.user_repository.get_by_email(
            request.email,
        )

        if existing_user:
            existing_membership = (
                self.member_repository.get_active_membership(
                    existing_user.id,
                )
            )

            if existing_membership:
                if existing_membership.workspace_id == workspace.id:
                    raise ValueError(
                        "This user is already a member of this workspace."
                    )
            
                raise ValueError(
                    "This user is already a member of another Agency or Brand. They must leave their current workspace before joining a new one."
                )

        invitation = WorkspaceInvitation(
            workspace_id=workspace.id,
            email=request.email,
            user_id=existing_user.id if existing_user else None,
            invited_by=current_user_id,
            role=WorkspaceRole(request.role.value),
            status=WorkspaceInvitationStatus.PENDING,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )

        return self.invitation_repository.create(invitation)
    
    def get_my_invitations(
        self,
        current_user_id: UUID,
    ):
        current_user = self.user_repository.get_by_id(
            current_user_id,
        )

        if current_user is None:
            raise ValueError("User not found.")

        invitations = (
            self.invitation_repository.get_by_email(
                current_user.email,
            )
        )

        return invitations
    
    def get_sent_invitations(
        self,
        current_user_id: UUID,
    ):
        current_user = self.user_repository.get_by_id(
            current_user_id,
        )

        if current_user is None:
            raise ValueError("User not found.")

        workspace = self.workspace_repository.get_by_owner(
            current_user_id,
        )

        if workspace is None:
            raise ValueError("Workspace not found.")

        membership = self.member_repository.get_by_workspace_and_user(
            workspace.id,
            current_user_id,
        )

        if membership is None:
            raise ValueError("Access denied.")

        if membership.role not in (
            WorkspaceRole.OWNER,
            WorkspaceRole.ADMIN,
        ):
            raise ValueError(
                "You don't have permission to view invitations."
            )

        return self.invitation_repository.get_by_workspace(
            workspace.id,
        )
    
    def accept_invitation(
        self,
        invitation_id: UUID,
        current_user_id: UUID,
    ) -> WorkspaceInvitation:

        invitation = self.invitation_repository.get_by_id(
            invitation_id,
        )

        if invitation is None:
            raise ValueError("Invitation not found.")

        if invitation.status != WorkspaceInvitationStatus.PENDING:
            raise ValueError("Invitation is no longer pending.")

        if invitation.expires_at < datetime.now(UTC):
            invitation.status = WorkspaceInvitationStatus.EXPIRED
            self.invitation_repository.save(invitation)

            raise ValueError("Invitation has expired.")

        current_user = self.user_repository.get_by_id(
            current_user_id,
        )

        if current_user is None:
            raise ValueError("User not found.")

        if current_user.email.lower() != invitation.email.lower():
            raise ValueError(
                "This invitation does not belong to your account."
            )

        existing_membership = (
            self.member_repository.get_active_membership(
                current_user.id,
            )
        )

        if existing_membership:
            raise ValueError(
                "You already belong to another Agency or Brand."
            )

        member = WorkspaceMember(
            workspace_id=invitation.workspace_id,
            user_id=current_user.id,
            role=invitation.role,
            status=WorkspaceMemberStatus.ACTIVE,
        )

        self.member_repository.create_member(member)

        invitation.user_id = current_user.id
        invitation.status = WorkspaceInvitationStatus.ACCEPTED

        self.invitation_repository.save(invitation)

        pending_invitations = (
            self.invitation_repository.get_by_email(
                current_user.email,
            )
        )

        for pending in pending_invitations:
            if pending.id == invitation.id:
                continue

            pending.status = WorkspaceInvitationStatus.CANCELLED
            self.invitation_repository.save(pending)

        return invitation
    
    
    def decline_invitation(
        self,
        invitation_id: UUID,
        current_user_id: UUID,
    ) -> WorkspaceInvitation:

        invitation = self.invitation_repository.get_by_id(
            invitation_id,
        )

        if invitation is None:
            raise ValueError("Invitation not found.")

        if invitation.status != WorkspaceInvitationStatus.PENDING:
            raise ValueError("Invitation is no longer pending.")

        if invitation.expires_at < datetime.now(UTC):
            invitation.status = WorkspaceInvitationStatus.EXPIRED
            self.invitation_repository.save(invitation)

            raise ValueError("Invitation has expired.")

        current_user = self.user_repository.get_by_id(
            current_user_id,
        )

        if current_user is None:
            raise ValueError("User not found.")

        if current_user.email.lower() != invitation.email.lower():
            raise ValueError(
                "This invitation does not belong to your account."
            )

        invitation.status = WorkspaceInvitationStatus.DECLINED

        return self.invitation_repository.save(
            invitation,
        )
    
    def cancel_invitation(
        self,
        invitation_id: UUID,
        current_user_id: UUID,
    ) -> WorkspaceInvitation:

        invitation = self.invitation_repository.get_by_id(
            invitation_id,
        )

        if invitation is None:
            raise ValueError("Invitation not found.")

        if invitation.status != WorkspaceInvitationStatus.PENDING:
            raise ValueError("Only pending invitations can be cancelled.")

        current_user = self.user_repository.get_by_id(
            current_user_id,
        )

        if current_user is None:
            raise ValueError("User not found.")

        workspace = self.workspace_repository.get_by_owner(
            current_user_id,
        )

        if workspace is None:
            raise ValueError("Workspace not found.")

        membership = self.member_repository.get_by_workspace_and_user(
            workspace.id,
            current_user_id,
        )

        if membership is None:
            raise ValueError("Access denied.")

        if membership.role not in (
            WorkspaceRole.OWNER,
            WorkspaceRole.ADMIN,
        ):
            raise ValueError(
                "You don't have permission to cancel invitations."
            )

        if invitation.workspace_id != workspace.id:
            raise ValueError(
                "You cannot cancel invitations from another workspace."
            )

        invitation.status = WorkspaceInvitationStatus.CANCELLED

        return self.invitation_repository.save(
            invitation,
        )
    
    def resend_invitation(
        self,
        invitation_id: UUID,
        current_user_id: UUID,
    ) -> WorkspaceInvitation:

        invitation = self.invitation_repository.get_by_id(
            invitation_id,
        )

        if invitation is None:
            raise ValueError("Invitation not found.")

        if invitation.status != WorkspaceInvitationStatus.PENDING:
            raise ValueError(
                "Only pending invitations can be resent."
            )

        current_user = self.user_repository.get_by_id(
            current_user_id,
        )

        if current_user is None:
            raise ValueError("User not found.")

        workspace = self.workspace_repository.get_by_owner(
            current_user_id,
        )

        if workspace is None:
            raise ValueError("Workspace not found.")

        membership = self.member_repository.get_by_workspace_and_user(
            workspace.id,
            current_user_id,
        )

        if membership is None:
            raise ValueError("Access denied.")

        if membership.role not in (
            WorkspaceRole.OWNER,
            WorkspaceRole.ADMIN,
        ):
            raise ValueError(
                "You don't have permission to resend invitations."
            )

        if invitation.workspace_id != workspace.id:
            raise ValueError(
                "You cannot resend invitations from another workspace."
            )

        invitation.token = secrets.token_urlsafe(32)
        invitation.expires_at = datetime.now(UTC) + timedelta(days=7)

        return self.invitation_repository.save(
            invitation,
        )