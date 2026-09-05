from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.database.repositories.user import UserRepository
from app.database.repositories.workspace import WorkspaceRepository
from app.database.repositories.workspace_invitation import (
    WorkspaceInvitationRepository,
)
from app.database.repositories.workspace_member import (
    WorkspaceMemberRepository,
)
from app.database.session import get_db
from app.schemas.workspace_invitation import (
    AcceptInvitationResponse,
    InvitationResponse,
    InviteMemberRequest,
)
from app.services.workspace_invitation import (
    WorkspaceInvitationService,
)

from app.schemas.workspace_invitation import (
    WorkspaceInvitationListResponse,
    WorkspaceInvitationItem,
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
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkspaceInvitationService(
        workspace_repository=WorkspaceRepository(db),
        member_repository=WorkspaceMemberRepository(db),
        invitation_repository=WorkspaceInvitationRepository(db),
        user_repository=UserRepository(db),
    )

    try:
        service.invite_member(
            current_user.id,
            request,
        )

        return InvitationResponse(
            message="Invitation sent successfully."
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    
@router.post(
    "/{invitation_id}/accept",
    response_model=AcceptInvitationResponse,
)
def accept_invitation(
    invitation_id: UUID,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkspaceInvitationService(
        workspace_repository=WorkspaceRepository(db),
        member_repository=WorkspaceMemberRepository(db),
        invitation_repository=WorkspaceInvitationRepository(db),
        user_repository=UserRepository(db),
    )

    try:
        service.accept_invitation(
            invitation_id,
            current_user.id,
        )

        return AcceptInvitationResponse(
            message="Invitation accepted successfully."
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    
@router.get(
    "",
    response_model=WorkspaceInvitationListResponse,
)
def get_my_invitations(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkspaceInvitationService(
        workspace_repository=WorkspaceRepository(db),
        member_repository=WorkspaceMemberRepository(db),
        invitation_repository=WorkspaceInvitationRepository(db),
        user_repository=UserRepository(db),
    )

    invitations = service.get_my_invitations(
        current_user.id,
    )

    return WorkspaceInvitationListResponse(
        invitations=[
            WorkspaceInvitationItem.model_validate(invitation)
            for invitation in invitations
        ]
    )