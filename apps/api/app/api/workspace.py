from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.database.models.user import User
from app.database.repositories.workspace import WorkspaceRepository
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
        WorkspaceRepository(db),
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