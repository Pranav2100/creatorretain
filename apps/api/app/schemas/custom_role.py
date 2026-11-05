from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.common.permissions import WorkspacePermission
from app.database.models.workspace_custom_role import (
    MAX_ROLE_NAME_LENGTH,
)


class PermissionInfo(BaseModel):
    """
    One permission, as something a person can be shown.

    The API hands these out rather than leaving the web app to
    keep its own copy of the list. A second copy is a second
    thing to forget: add a permission to the backend, forget the
    frontend, and the checkbox for it silently never appears.
    """

    value: str
    label: str
    description: str
    # Whether the person asking holds it. A permission you cannot
    # grant is shown but not offerable, which is less confusing
    # than a list that silently differs per person.
    held: bool


class CustomRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    position: int
    permissions: list[str]
    member_count: int = 0
    # Whether the person asking could edit or hand out this role.
    # Decided by the server, because the rule is the server's.
    editable: bool = False


class CustomRoleListResponse(BaseModel):
    roles: list[CustomRoleResponse]
    permissions: list[PermissionInfo]


class CreateRoleRequest(BaseModel):
    name: str = Field(min_length=1, max_length=MAX_ROLE_NAME_LENGTH)
    permissions: list[str] = Field(min_length=1)


class UpdateRoleRequest(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_ROLE_NAME_LENGTH,
    )
    permissions: list[str] | None = None


class ReorderRolesRequest(BaseModel):
    # The whole list, in the order wanted. Sending a partial list
    # would leave the rest at positions that mean nothing.
    role_ids: list[UUID] = Field(min_length=1)


class GrantRoleRequest(BaseModel):
    role_id: UUID


# What each permission is called where a person can see it.
# Kept beside the schema rather than in the enum, because the
# enum is the rule and this is the wording.
PERMISSION_LABELS: dict[WorkspacePermission, tuple[str, str]] = {
    WorkspacePermission.EDIT_WORKSPACE: (
        "Edit the workspace",
        "Change the name, bio and logo creators see on an offer.",
    ),
    WorkspacePermission.VIEW_MEMBERS: (
        "See the team",
        "View who is in this workspace and what they hold.",
    ),
    WorkspacePermission.INVITE_MEMBERS: (
        "Invite people",
        "Send invitations to join this workspace.",
    ),
    WorkspacePermission.MANAGE_INVITATIONS: (
        "Manage invitations",
        "Resend and cancel invitations that are waiting.",
    ),
    WorkspacePermission.REMOVE_MEMBERS: (
        "Remove people",
        "Take someone out of the workspace. Never someone above you.",
    ),
    WorkspacePermission.CHANGE_ROLES: (
        "Manage roles",
        "Change what people hold, and define roles like this one.",
    ),
    WorkspacePermission.TRANSFER_OWNERSHIP: (
        "Transfer ownership",
        "Hand the workspace to somebody else.",
    ),
    WorkspacePermission.MANAGE_BILLING: (
        "Manage billing",
        "Change the plan and the payment details.",
    ),
    WorkspacePermission.DELETE_WORKSPACE: (
        "Delete the workspace",
        "Close the workspace and everything in it.",
    ),
    WorkspacePermission.LEAVE_WORKSPACE: (
        "Leave the workspace",
        "Walk out without being removed.",
    ),
    WorkspacePermission.VIEW_RETAINERS: (
        "See retainers",
        "Read retainers, what was agreed and what is due.",
    ),
    WorkspacePermission.MANAGE_RETAINERS: (
        "Run retainers",
        "Offer, pause, end and review the work on a retainer.",
    ),
    WorkspacePermission.ASSIGN_RETAINERS: (
        "Assign accounts",
        "Decide who runs which creator.",
    ),
    WorkspacePermission.VIEW_ALL_RETAINERS: (
        "See every retainer",
        "Not only the accounts put in their hands.",
    ),
}
