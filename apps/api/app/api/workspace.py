from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.database.models.user import User
from app.database.repositories.workspace import WorkspaceRepository
from app.database.repositories.workspace_member import (WorkspaceMemberRepository,)
from app.services.workspace_member import WorkspaceMemberService
from app.database.session import get_db
from app.schemas.workspace import (
    CreateWorkspaceRequest,
    CreateWorkspaceResponse,
    WorkspaceResponse,
)
from app.services.workspace import WorkspaceService

router = APIRouter(
    prefix="/workspaces",
    tags=["Workspaces"],
)


@router.get("/check-username/{username}")
def check_username(
    username: str,
    db: Session = Depends(get_db),
):
    service = WorkspaceService(
    repository=WorkspaceRepository(db),
    member_service=WorkspaceMemberService(
        WorkspaceMemberRepository(db),
    ),
)

    return service.check_username(username)


@router.get(
    "/me",
    response_model=WorkspaceResponse,
)
def get_my_workspace(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkspaceService(
    repository=WorkspaceRepository(db),
    member_service=WorkspaceMemberService(
        WorkspaceMemberRepository(db),
    ),
)

    try:
        workspace = service.get_my_workspace(
            current_user.id,
        )

        return WorkspaceResponse.model_validate(workspace)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "",
    response_model=CreateWorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workspace(
    request: CreateWorkspaceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkspaceService(
    repository=WorkspaceRepository(db),
    member_service=WorkspaceMemberService(
        WorkspaceMemberRepository(db),
    ),
)

    try:
        workspace = service.create(
            owner_user_id=current_user.id,
            request=request,
        )

        return CreateWorkspaceResponse(
            message="Workspace created successfully.",
            workspace=WorkspaceResponse.model_validate(workspace),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )