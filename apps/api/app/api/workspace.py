from fastapi import APIRouter, Depends, status

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_workspace_service
from app.api.errors import http_error
from app.database.models.user import User
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
    service: WorkspaceService = Depends(get_workspace_service),
):
    return service.check_username(username)


@router.get(
    "/me",
    response_model=WorkspaceResponse,
)
def get_my_workspace(
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        workspace = service.get_my_workspace(
            current_user.id,
        )

        return WorkspaceResponse.model_validate(workspace)

    except ValueError as e:
        raise http_error(e)


@router.post(
    "",
    response_model=CreateWorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workspace(
    request: CreateWorkspaceRequest,
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
):
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
        raise http_error(e)
