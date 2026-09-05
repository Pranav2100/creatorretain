from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import (
    get_workspace_invitation_service,
)
from app.api.errors import http_error
from app.database.models.user import User
from app.database.repositories.user import UserRepository
from app.database.session import get_db
from app.schemas.workspace_invitation import (
    AcceptByTokenRequest,
    AcceptInvitationResponse,
    InvitationPreviewResponse,
    InvitationResponse,
    InviteMemberRequest,
    SentInvitationItem,
    SentInvitationListResponse,
    WorkspaceInvitationItem,
    WorkspaceInvitationListResponse,
)
from app.services.workspace_invitation import (
    WorkspaceInvitationService,
)

router = APIRouter(
    prefix="/workspace-invitations",
    tags=["Workspace Invitations"],
)


@router.post(
    "/invite",
    response_model=InvitationResponse,
)
def invite_member(
    request: InviteMemberRequest,
    current_user: User = Depends(get_current_user),
    service: WorkspaceInvitationService = Depends(
        get_workspace_invitation_service,
    ),
):
    try:
        service.invite_member(
            current_user.id,
            request,
        )

        return InvitationResponse(
            message="Invitation sent successfully.",
        )

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/{invitation_id}/accept",
    response_model=AcceptInvitationResponse,
)
def accept_invitation(
    invitation_id: UUID,
    current_user: User = Depends(get_current_user),
    service: WorkspaceInvitationService = Depends(
        get_workspace_invitation_service,
    ),
):
    try:
        service.accept_invitation(
            invitation_id,
            current_user.id,
        )

        return AcceptInvitationResponse(
            message="Invitation accepted successfully.",
        )

    except ValueError as e:
        raise http_error(e)


@router.get(
    "/token/{token}",
    response_model=InvitationPreviewResponse,
)
def preview_invitation(
    token: str,
    db: Session = Depends(get_db),
    service: WorkspaceInvitationService = Depends(
        get_workspace_invitation_service,
    ),
):
    """
    Public. Lets an invitation link show who invited whom before
    the recipient has signed in or created an account.
    """
    try:
        invitation = service.preview_by_token(token)

        existing_user = UserRepository(db).get_by_email(
            invitation.email,
        )

        return InvitationPreviewResponse.from_invitation(
            invitation,
            requires_signup=existing_user is None,
        )

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/accept-by-token",
    response_model=AcceptInvitationResponse,
)
def accept_by_token(
    request: AcceptByTokenRequest,
    current_user: User = Depends(get_current_user),
    service: WorkspaceInvitationService = Depends(
        get_workspace_invitation_service,
    ),
):
    try:
        service.accept_by_token(
            request.token,
            current_user.id,
        )

        return AcceptInvitationResponse(
            message="Invitation accepted successfully.",
        )

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/{invitation_id}/decline",
    response_model=InvitationResponse,
)
def decline_invitation(
    invitation_id: UUID,
    current_user: User = Depends(get_current_user),
    service: WorkspaceInvitationService = Depends(
        get_workspace_invitation_service,
    ),
):
    try:
        service.decline_invitation(
            invitation_id,
            current_user.id,
        )

        return InvitationResponse(
            message="Invitation declined successfully.",
        )

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/{invitation_id}/cancel",
    response_model=InvitationResponse,
)
def cancel_invitation(
    invitation_id: UUID,
    current_user: User = Depends(get_current_user),
    service: WorkspaceInvitationService = Depends(
        get_workspace_invitation_service,
    ),
):
    try:
        service.cancel_invitation(
            invitation_id,
            current_user.id,
        )

        return InvitationResponse(
            message="Invitation cancelled successfully.",
        )

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/{invitation_id}/resend",
    response_model=InvitationResponse,
)
def resend_invitation(
    invitation_id: UUID,
    current_user: User = Depends(get_current_user),
    service: WorkspaceInvitationService = Depends(
        get_workspace_invitation_service,
    ),
):
    try:
        service.resend_invitation(
            invitation_id,
            current_user.id,
        )

        return InvitationResponse(
            message="Invitation resent successfully.",
        )

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/{invitation_id}/request-resend",
    response_model=InvitationResponse,
)
def request_resend(
    invitation_id: UUID,
    current_user: User = Depends(get_current_user),
    service: WorkspaceInvitationService = Depends(
        get_workspace_invitation_service,
    ),
):
    try:
        service.request_resend(
            invitation_id,
            current_user.id,
        )

        return InvitationResponse(
            message=(
                "We've let the workspace know you'd like this "
                "invitation resent."
            ),
        )

    except ValueError as e:
        raise http_error(e)


@router.get(
    "",
    response_model=WorkspaceInvitationListResponse,
)
def get_my_invitations(
    current_user: User = Depends(get_current_user),
    service: WorkspaceInvitationService = Depends(
        get_workspace_invitation_service,
    ),
):
    try:
        invitations = service.get_my_invitations(
            current_user.id,
        )

        return WorkspaceInvitationListResponse(
            invitations=[
                WorkspaceInvitationItem.from_invitation(invitation)
                for invitation in invitations
            ]
        )

    except ValueError as e:
        raise http_error(e)


@router.get(
    "/sent",
    response_model=SentInvitationListResponse,
)
def get_sent_invitations(
    current_user: User = Depends(get_current_user),
    service: WorkspaceInvitationService = Depends(
        get_workspace_invitation_service,
    ),
):
    try:
        invitations = service.get_sent_invitations(
            current_user.id,
        )

        return SentInvitationListResponse(
            invitations=[
                SentInvitationItem.from_invitation(invitation)
                for invitation in invitations
            ]
        )

    except ValueError as e:
        raise http_error(e)
