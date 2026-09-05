from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.repositories.user import UserRepository
from app.database.repositories.workspace import WorkspaceRepository
from app.database.repositories.workspace_invitation import (
    WorkspaceInvitationRepository,
)
from app.database.repositories.workspace_member import (
    WorkspaceMemberRepository,
)
from app.database.session import get_db
from app.services.email import get_email_sender
from app.services.workspace import WorkspaceService
from app.services.workspace_invitation import (
    WorkspaceInvitationService,
)
from app.services.workspace_member import WorkspaceMemberService


def get_workspace_member_service(
    db: Session = Depends(get_db),
) -> WorkspaceMemberService:
    return WorkspaceMemberService(
        repository=WorkspaceMemberRepository(db),
        workspace_repository=WorkspaceRepository(db),
    )


def get_workspace_service(
    db: Session = Depends(get_db),
) -> WorkspaceService:
    return WorkspaceService(
        repository=WorkspaceRepository(db),
        member_service=get_workspace_member_service(db),
    )


def get_workspace_invitation_service(
    db: Session = Depends(get_db),
) -> WorkspaceInvitationService:
    return WorkspaceInvitationService(
        workspace_repository=WorkspaceRepository(db),
        member_repository=WorkspaceMemberRepository(db),
        invitation_repository=WorkspaceInvitationRepository(db),
        user_repository=UserRepository(db),
        member_service=get_workspace_member_service(db),
        email_sender=get_email_sender(),
    )
