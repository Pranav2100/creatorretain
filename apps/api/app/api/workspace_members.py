from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import (
    get_workspace_member_service,
)
from app.api.errors import http_error
from app.common.enums import WorkspaceRole
from app.database.models.user import User
from app.schemas.workspace_member import (
    ChangeMemberRoleRequest,
    WorkspaceMemberItem,
    WorkspaceMemberListResponse,
    WorkspaceMemberResponse,
)
from app.services.workspace_member import WorkspaceMemberService

router = APIRouter(
    prefix="/workspace-members",
    tags=["Workspace Members"],
)


@router.get(
    "",
    response_model=WorkspaceMemberListResponse,
)
def list_members(
    current_user: User = Depends(get_current_user),
    service: WorkspaceMemberService = Depends(
        get_workspace_member_service,
    ),
):
    try:
        members = service.list_members(current_user.id)

        return WorkspaceMemberListResponse(
            members=[
                WorkspaceMemberItem.from_member(member)
                for member in members
            ]
        )

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/leave",
    response_model=WorkspaceMemberResponse,
)
def leave_workspace(
    current_user: User = Depends(get_current_user),
    service: WorkspaceMemberService = Depends(
        get_workspace_member_service,
    ),
):
    try:
        service.leave_workspace(current_user.id)

        return WorkspaceMemberResponse(
            message="You have left the workspace.",
        )

    except ValueError as e:
        raise http_error(e)


@router.patch(
    "/{member_id}/role",
    response_model=WorkspaceMemberResponse,
)
def change_member_role(
    member_id: UUID,
    request: ChangeMemberRoleRequest,
    current_user: User = Depends(get_current_user),
    service: WorkspaceMemberService = Depends(
        get_workspace_member_service,
    ),
):
    try:
        member = service.change_member_role(
            current_user_id=current_user.id,
            member_id=member_id,
            new_role=WorkspaceRole(request.role.value),
        )

        return WorkspaceMemberResponse(
            message=f"Member role changed to {member.role.value}.",
        )

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/{member_id}/transfer-ownership",
    response_model=WorkspaceMemberResponse,
)
def transfer_ownership(
    member_id: UUID,
    current_user: User = Depends(get_current_user),
    service: WorkspaceMemberService = Depends(
        get_workspace_member_service,
    ),
):
    try:
        service.transfer_ownership(
            current_user_id=current_user.id,
            member_id=member_id,
        )

        return WorkspaceMemberResponse(
            message="Ownership transferred successfully.",
        )

    except ValueError as e:
        raise http_error(e)


@router.delete(
    "/{member_id}",
    response_model=WorkspaceMemberResponse,
)
def remove_member(
    member_id: UUID,
    current_user: User = Depends(get_current_user),
    service: WorkspaceMemberService = Depends(
        get_workspace_member_service,
    ),
):
    try:
        service.remove_member(
            current_user_id=current_user.id,
            member_id=member_id,
        )

        return WorkspaceMemberResponse(
            message="Member removed successfully.",
        )

    except ValueError as e:
        raise http_error(e)
