from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import (
    get_custom_role_service,
    get_workspace_member_service,
)
from app.api.errors import http_error
from app.common.permissions import (
    WorkspacePermission,
    can_shape_role,
)
from app.database.models.user import User
from app.database.models.workspace_custom_role import (
    WorkspaceCustomRole,
)
from app.schemas.custom_role import (
    PERMISSION_LABELS,
    CreateRoleRequest,
    CustomRoleListResponse,
    CustomRoleResponse,
    GrantRoleRequest,
    PermissionInfo,
    ReorderRolesRequest,
    UpdateRoleRequest,
)
from app.services.custom_role import CustomRoleService
from app.services.workspace_member import (
    WorkspaceContext,
    WorkspaceMemberService,
)

router = APIRouter(prefix="/workspace-roles", tags=["Roles"])


def _shown(
    role: WorkspaceCustomRole,
    context: WorkspaceContext,
    holders: int,
) -> CustomRoleResponse:
    return CustomRoleResponse(
        id=role.id,
        name=role.name,
        position=role.position,
        permissions=sorted(p.value for p in role.granted),
        member_count=holders,
        # The same rule the service will apply if they try. Sent
        # so the interface can grey a row out rather than let
        # somebody fill in a form that was always going to be
        # refused.
        editable=can_shape_role(
            context.permissions,
            role.granted,
            role.granted,
        ),
    )


@router.get(
    "",
    response_model=CustomRoleListResponse,
    summary="The roles this workspace has invented",
)
def list_roles(
    current_user: User = Depends(get_current_user),
    service: CustomRoleService = Depends(get_custom_role_service),
    members: WorkspaceMemberService = Depends(
        get_workspace_member_service
    ),
):
    """
    The roles, and the full set of permissions to build them from.

    Both together, because a page that lists roles always needs
    the vocabulary as well - and the vocabulary is the server's
    to define, not something the web app should keep its own
    copy of.
    """
    try:
        context = members.resolve_context(current_user.id)
        roles = service.list_roles(context)

        counts = {
            role.id: service.repository.holder_count(role.id)
            for role in roles
        }

        return CustomRoleListResponse(
            roles=[
                _shown(role, context, counts[role.id])
                for role in roles
            ],
            permissions=[
                PermissionInfo(
                    value=permission.value,
                    label=PERMISSION_LABELS[permission][0],
                    description=PERMISSION_LABELS[permission][1],
                    held=permission in context.permissions,
                )
                for permission in WorkspacePermission
                if permission in PERMISSION_LABELS
            ],
        )

    except ValueError as e:
        raise http_error(e)


@router.get(
    "/assignments",
    summary="Who holds which role",
)
def list_assignments(
    current_user: User = Depends(get_current_user),
    service: CustomRoleService = Depends(get_custom_role_service),
    members: WorkspaceMemberService = Depends(
        get_workspace_member_service
    ),
):
    """
    Every live grant in the workspace, keyed by user.

    One call for the whole Team list. Asking per person would be
    a query per row, and the list already knows every user it is
    about to draw.
    """
    try:
        context = members.resolve_context(current_user.id)
        held = service.roles_by_user(context)

        return {
            "assignments": {
                str(user_id): [str(role.id) for role in roles]
                for user_id, roles in held.items()
            }
        }

    except ValueError as e:
        raise http_error(e)


@router.post(
    "",
    response_model=CustomRoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invent a role",
)
def create_role(
    payload: CreateRoleRequest,
    current_user: User = Depends(get_current_user),
    service: CustomRoleService = Depends(get_custom_role_service),
    members: WorkspaceMemberService = Depends(
        get_workspace_member_service
    ),
):
    try:
        context = members.resolve_context(current_user.id)
        role = service.create_role(
            context,
            name=payload.name,
            permissions=payload.permissions,
        )
        service.repository.db.commit()

        return _shown(role, context, 0)

    except ValueError as e:
        raise http_error(e)


@router.patch(
    "/{role_id}",
    response_model=CustomRoleResponse,
    summary="Rename a role or change what it grants",
)
def update_role(
    role_id: UUID,
    payload: UpdateRoleRequest,
    current_user: User = Depends(get_current_user),
    service: CustomRoleService = Depends(get_custom_role_service),
    members: WorkspaceMemberService = Depends(
        get_workspace_member_service
    ),
):
    try:
        context = members.resolve_context(current_user.id)
        role = service.update_role(
            context,
            role_id,
            name=payload.name,
            permissions=payload.permissions,
        )
        service.repository.db.commit()

        return _shown(
            role,
            context,
            service.repository.holder_count(role.id),
        )

    except ValueError as e:
        raise http_error(e)


@router.put(
    "/order",
    response_model=list[CustomRoleResponse],
    summary="Put the roles in this order",
)
def reorder_roles(
    payload: ReorderRolesRequest,
    current_user: User = Depends(get_current_user),
    service: CustomRoleService = Depends(get_custom_role_service),
    members: WorkspaceMemberService = Depends(
        get_workspace_member_service
    ),
):
    try:
        context = members.resolve_context(current_user.id)
        roles = service.reorder(context, payload.role_ids)
        service.repository.db.commit()

        return [
            _shown(
                role,
                context,
                service.repository.holder_count(role.id),
            )
            for role in roles
        ]

    except ValueError as e:
        raise http_error(e)


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a role",
)
def delete_role(
    role_id: UUID,
    current_user: User = Depends(get_current_user),
    service: CustomRoleService = Depends(get_custom_role_service),
    members: WorkspaceMemberService = Depends(
        get_workspace_member_service
    ),
):
    try:
        context = members.resolve_context(current_user.id)
        service.delete_role(context, role_id)
        service.repository.db.commit()

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Give somebody a role",
)
def grant_role(
    user_id: UUID,
    payload: GrantRoleRequest,
    current_user: User = Depends(get_current_user),
    service: CustomRoleService = Depends(get_custom_role_service),
    members: WorkspaceMemberService = Depends(
        get_workspace_member_service
    ),
):
    try:
        context = members.resolve_context(current_user.id)
        service.grant(context, user_id, payload.role_id)
        service.repository.db.commit()

    except ValueError as e:
        raise http_error(e)


@router.delete(
    "/members/{user_id}/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Take a role back",
)
def revoke_role(
    user_id: UUID,
    role_id: UUID,
    current_user: User = Depends(get_current_user),
    service: CustomRoleService = Depends(get_custom_role_service),
    members: WorkspaceMemberService = Depends(
        get_workspace_member_service
    ),
):
    try:
        context = members.resolve_context(current_user.id)
        service.revoke(context, user_id, role_id)
        service.repository.db.commit()

    except ValueError as e:
        raise http_error(e)
