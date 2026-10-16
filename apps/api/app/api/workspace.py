from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_workspace_service
from app.api.errors import http_error
from app.common.utils.images import MAX_IMAGE_BYTES
from app.database.models.user import User
from app.services.storage import FileStore, get_file_store
from app.schemas.workspace import (
    CreateWorkspaceRequest,
    CreateWorkspaceResponse,
    MyWorkspaceResponse,
    UpdateWorkspaceRequest,
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
    response_model=MyWorkspaceResponse,
)
def get_my_workspace(
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        context = service.my_context(current_user.id)

        return MyWorkspaceResponse(
            **WorkspaceResponse.model_validate(
                context.workspace,
            ).model_dump(),
            your_role=context.role,
        )

    except ValueError as e:
        raise http_error(e)


@router.put(
    "",
    response_model=WorkspaceResponse,
)
def update_workspace(
    request: UpdateWorkspaceRequest,
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
):
    try:
        # exclude_unset, not exclude_none: a null that was actually
        # sent means "clear this", and the service needs to tell
        # that apart from a field nobody mentioned.
        workspace = service.update(
            current_user.id,
            **request.model_dump(exclude_unset=True),
        )

        return WorkspaceResponse.model_validate(workspace)

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/logo",
    response_model=WorkspaceResponse,
)
async def upload_logo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
    file_store: FileStore = Depends(get_file_store),
):
    # Read with a ceiling rather than reading it all and measuring
    # afterwards: a 400MB upload should not become 400MB of this
    # process's memory before being told no.
    data = await file.read(MAX_IMAGE_BYTES + 1)

    try:
        workspace = service.set_logo(
            current_user.id,
            data=data,
            file_store=file_store,
        )

        return WorkspaceResponse.model_validate(workspace)

    except ValueError as e:
        raise http_error(e)


@router.delete(
    "/logo",
    response_model=WorkspaceResponse,
)
def remove_logo(
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
    file_store: FileStore = Depends(get_file_store),
):
    try:
        workspace = service.clear_logo(
            current_user.id,
            file_store=file_store,
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
