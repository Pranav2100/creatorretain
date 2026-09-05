from enum import StrEnum

from app.common.enums import WorkspaceRole


class WorkspacePermission(StrEnum):
    VIEW_MEMBERS = "view_members"
    INVITE_MEMBERS = "invite_members"
    MANAGE_INVITATIONS = "manage_invitations"
    REMOVE_MEMBERS = "remove_members"
    CHANGE_ROLES = "change_roles"
    TRANSFER_OWNERSHIP = "transfer_ownership"
    DELETE_WORKSPACE = "delete_workspace"
    LEAVE_WORKSPACE = "leave_workspace"


ROLE_PERMISSIONS: dict[WorkspaceRole, frozenset[WorkspacePermission]] = {
    WorkspaceRole.OWNER: frozenset(
        {
            WorkspacePermission.VIEW_MEMBERS,
            WorkspacePermission.INVITE_MEMBERS,
            WorkspacePermission.MANAGE_INVITATIONS,
            WorkspacePermission.REMOVE_MEMBERS,
            WorkspacePermission.CHANGE_ROLES,
            WorkspacePermission.TRANSFER_OWNERSHIP,
            WorkspacePermission.DELETE_WORKSPACE,
        }
    ),
    WorkspaceRole.ADMIN: frozenset(
        {
            WorkspacePermission.VIEW_MEMBERS,
            WorkspacePermission.INVITE_MEMBERS,
            WorkspacePermission.MANAGE_INVITATIONS,
            WorkspacePermission.REMOVE_MEMBERS,
            WorkspacePermission.CHANGE_ROLES,
            WorkspacePermission.LEAVE_WORKSPACE,
        }
    ),
    WorkspaceRole.MEMBER: frozenset(
        {
            WorkspacePermission.LEAVE_WORKSPACE,
        }
    ),
}


def has_permission(
    role: WorkspaceRole,
    permission: WorkspacePermission,
) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def can_remove_member(
    actor_role: WorkspaceRole,
    target_role: WorkspaceRole,
) -> bool:
    """
    The Owner can remove Admins and Members.
    Admins can only remove regular Members.
    Nobody can remove the Owner.
    """
    if target_role == WorkspaceRole.OWNER:
        return False

    if actor_role == WorkspaceRole.OWNER:
        return True

    if actor_role == WorkspaceRole.ADMIN:
        return target_role == WorkspaceRole.MEMBER

    return False


def can_change_role(
    actor_role: WorkspaceRole,
    target_role: WorkspaceRole,
    new_role: WorkspaceRole,
) -> bool:
    """
    The Owner can promote Members and demote Admins.
    Admins can only promote Members to Admin.
    The Owner's role is only changed through ownership transfer.
    """
    if WorkspaceRole.OWNER in (target_role, new_role):
        return False

    if actor_role == WorkspaceRole.OWNER:
        return True

    if actor_role == WorkspaceRole.ADMIN:
        return (
            target_role == WorkspaceRole.MEMBER
            and new_role == WorkspaceRole.ADMIN
        )

    return False
