import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.common.enums import (
    WorkspaceInvitationStatus,
    WorkspaceRole,
    WorkspaceType,
)
from app.common.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.common.permissions import WorkspacePermission
from app.database.models.workspace_invitation import WorkspaceInvitation
from app.database.repositories.user import UserRepository
from app.database.repositories.workspace import WorkspaceRepository
from app.database.repositories.workspace_invitation import (
    WorkspaceInvitationRepository,
)
from app.database.repositories.workspace_member import (
    WorkspaceMemberRepository,
)
from app.schemas.workspace_invitation import InviteMemberRequest
from app.services.workspace_member import (
    WorkspaceContext,
    WorkspaceMemberService,
)

INVITATION_TTL = timedelta(days=30)


class WorkspaceInvitationService:
    def __init__(
        self,
        workspace_repository: WorkspaceRepository,
        member_repository: WorkspaceMemberRepository,
        invitation_repository: WorkspaceInvitationRepository,
        user_repository: UserRepository,
        member_service: WorkspaceMemberService,
    ):
        self.workspace_repository = workspace_repository
        self.member_repository = member_repository
        self.invitation_repository = invitation_repository
        self.user_repository = user_repository
        self.member_service = member_service

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    def invite_member(
        self,
        current_user_id: UUID,
        request: InviteMemberRequest,
    ) -> WorkspaceInvitation:
        request.email = request.email.lower().strip()

        current_user = self._get_user(current_user_id)

        if current_user.email.lower() == request.email:
            raise ConflictError("You cannot invite yourself.")

        context = self._require(
            current_user_id,
            WorkspacePermission.INVITE_MEMBERS,
        )

        if context.workspace.workspace_type == WorkspaceType.CREATOR:
            raise PermissionDeniedError(
                "Creator workspaces cannot invite members."
            )

        existing_invitation = (
            self.invitation_repository.get_pending_by_workspace_and_email(
                context.workspace_id,
                request.email,
            )
        )

        if existing_invitation is not None:
            raise ConflictError(
                "An active invitation already exists."
            )

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
                if (
                    existing_membership.workspace_id
                    == context.workspace_id
                ):
                    raise ConflictError(
                        "This user is already a member of this workspace."
                    )

                raise ConflictError(
                    "This user is already a member of another Agency or "
                    "Brand. They must leave their current workspace "
                    "before joining a new one."
                )

        invitation = WorkspaceInvitation(
            workspace_id=context.workspace_id,
            email=request.email,
            user_id=existing_user.id if existing_user else None,
            invited_by=current_user_id,
            role=WorkspaceRole(request.role.value),
            status=WorkspaceInvitationStatus.PENDING,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.now(UTC) + INVITATION_TTL,
        )

        return self.invitation_repository.create(invitation)

    def resend_invitation(
        self,
        invitation_id: UUID,
        current_user_id: UUID,
    ) -> WorkspaceInvitation:
        invitation = self._get_managed_invitation(
            invitation_id,
            current_user_id,
        )

        if invitation.status not in (
            WorkspaceInvitationStatus.PENDING,
            WorkspaceInvitationStatus.EXPIRED,
        ):
            raise ConflictError(
                f"A {invitation.status.value} invitation cannot be "
                "resent. Send a new invitation instead."
            )

        invitation.token = secrets.token_urlsafe(32)
        invitation.expires_at = datetime.now(UTC) + INVITATION_TTL
        invitation.status = WorkspaceInvitationStatus.PENDING
        invitation.resend_requested_at = None

        return self.invitation_repository.save(invitation)

    def request_resend(
        self,
        invitation_id: UUID,
        current_user_id: UUID,
    ) -> WorkspaceInvitation:
        """
        Lets the recipient of a lapsed invitation ask the workspace
        to send it again, instead of silently losing the connection.
        """
        invitation = self.invitation_repository.get_by_id(
            invitation_id,
        )

        if invitation is None:
            raise NotFoundError("Invitation not found.")

        current_user = self._get_user(current_user_id)

        if current_user.email.lower() != invitation.email.lower():
            raise PermissionDeniedError(
                "This invitation does not belong to your account."
            )

        status = invitation.effective_status

        if status == WorkspaceInvitationStatus.PENDING:
            raise ConflictError(
                "This invitation is still open. You can accept it."
            )

        if status != WorkspaceInvitationStatus.EXPIRED:
            raise ConflictError(
                f"A {status.value} invitation cannot be revived."
            )

        if invitation.resend_requested_at is not None:
            raise ConflictError(
                "You have already asked for this to be resent."
            )

        invitation.status = WorkspaceInvitationStatus.EXPIRED
        invitation.resend_requested_at = datetime.now(UTC)

        return self.invitation_repository.save(invitation)

    def cancel_invitation(
        self,
        invitation_id: UUID,
        current_user_id: UUID,
    ) -> WorkspaceInvitation:
        invitation = self._get_managed_invitation(
            invitation_id,
            current_user_id,
        )

        if invitation.status != WorkspaceInvitationStatus.PENDING:
            raise ConflictError(
                "Only pending invitations can be cancelled."
            )

        invitation.status = WorkspaceInvitationStatus.CANCELLED

        return self.invitation_repository.save(invitation)

    # ------------------------------------------------------------------
    # Receiving
    # ------------------------------------------------------------------

    def accept_invitation(
        self,
        invitation_id: UUID,
        current_user_id: UUID,
    ) -> WorkspaceInvitation:
        invitation = self._get_own_pending_invitation(
            invitation_id,
            current_user_id,
        )

        existing_membership = (
            self.member_repository.get_active_membership(
                current_user_id,
            )
        )

        if existing_membership:
            raise ConflictError(
                "You already belong to another Agency or Brand."
            )

        self.member_service.activate_member(
            workspace_id=invitation.workspace_id,
            user_id=current_user_id,
            role=invitation.role,
        )

        invitation.user_id = current_user_id
        invitation.status = WorkspaceInvitationStatus.ACCEPTED

        self.invitation_repository.save(invitation)

        # A user can only belong to one workspace, so any other
        # pending invitation is now moot.
        for pending in (
            self.invitation_repository.get_live_pending_by_email(
                invitation.email,
            )
        ):
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
        invitation = self._get_own_pending_invitation(
            invitation_id,
            current_user_id,
        )

        invitation.status = WorkspaceInvitationStatus.DECLINED

        return self.invitation_repository.save(invitation)

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def get_my_invitations(
        self,
        current_user_id: UUID,
    ) -> list[WorkspaceInvitation]:
        current_user = self._get_user(current_user_id)

        return self.invitation_repository.get_by_email(
            current_user.email,
        )

    def get_sent_invitations(
        self,
        current_user_id: UUID,
    ) -> list[WorkspaceInvitation]:
        context = self._require(
            current_user_id,
            WorkspacePermission.MANAGE_INVITATIONS,
        )

        return self.invitation_repository.get_by_workspace(
            context.workspace_id,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_user(self, user_id: UUID):
        user = self.user_repository.get_by_id(user_id)

        if user is None:
            raise NotFoundError("User not found.")

        return user

    def _require(
        self,
        current_user_id: UUID,
        permission: WorkspacePermission,
    ) -> WorkspaceContext:
        context = self.member_service.resolve_context(
            current_user_id,
        )

        context.require(permission)

        return context

    def _get_managed_invitation(
        self,
        invitation_id: UUID,
        current_user_id: UUID,
    ) -> WorkspaceInvitation:
        context = self._require(
            current_user_id,
            WorkspacePermission.MANAGE_INVITATIONS,
        )

        invitation = self.invitation_repository.get_by_id(
            invitation_id,
        )

        if (
            invitation is None
            or invitation.workspace_id != context.workspace_id
        ):
            raise NotFoundError("Invitation not found.")

        return invitation

    def _get_own_pending_invitation(
        self,
        invitation_id: UUID,
        current_user_id: UUID,
    ) -> WorkspaceInvitation:
        invitation = self.invitation_repository.get_by_id(
            invitation_id,
        )

        if invitation is None:
            raise NotFoundError("Invitation not found.")

        current_user = self._get_user(current_user_id)

        if current_user.email.lower() != invitation.email.lower():
            raise PermissionDeniedError(
                "This invitation does not belong to your account."
            )

        if invitation.status != WorkspaceInvitationStatus.PENDING:
            raise ConflictError("Invitation is no longer pending.")

        if invitation.expires_at < datetime.now(UTC):
            invitation.status = WorkspaceInvitationStatus.EXPIRED
            self.invitation_repository.save(invitation)

            raise ConflictError("Invitation has expired.")

        return invitation
