from dataclasses import dataclass
from uuid import UUID

from app.common.enums import (
    WorkspaceMemberStatus,
    WorkspaceRole,
)
from app.common.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.common.permissions import (
    WorkspacePermission,
    can_change_role,
    can_remove_member,
    has_permission,
)
from app.database.models.workspace import Workspace
from app.database.models.workspace_member import WorkspaceMember
from app.database.repositories.workspace import WorkspaceRepository
from app.database.repositories.workspace_member import (
    WorkspaceMemberRepository,
)


@dataclass(frozen=True)
class WorkspaceContext:
    """
    The workspace the current user is acting in, together with
    the role they hold in it.

    Resolution goes:
        current user -> active membership -> workspace -> role

    rather than looking the workspace up by owner, so Admins and
    Members resolve to the same workspace as the Owner.
    """

    workspace: Workspace
    membership: WorkspaceMember | None
    role: WorkspaceRole

    @property
    def workspace_id(self) -> UUID:
        return self.workspace.id

    def require(self, permission: WorkspacePermission) -> None:
        if not has_permission(self.role, permission):
            raise PermissionDeniedError(
                "You don't have permission to perform this action."
            )


class WorkspaceMemberService:
    def __init__(
        self,
        repository: WorkspaceMemberRepository,
        workspace_repository: WorkspaceRepository,
    ):
        self.repository = repository
        self.workspace_repository = workspace_repository

    # ------------------------------------------------------------------
    # Workspace resolution
    # ------------------------------------------------------------------

    def resolve_context(
        self,
        current_user_id: UUID,
    ) -> WorkspaceContext:
        membership = self.repository.get_active_membership(
            current_user_id,
        )

        if membership is not None:
            workspace = self.workspace_repository.get(
                membership.workspace_id,
            )

            if workspace is None or workspace.deleted_at is not None:
                raise NotFoundError("Workspace not found.")

            return WorkspaceContext(
                workspace=workspace,
                membership=membership,
                role=membership.role,
            )

        # Fallback for workspaces created before owner membership
        # rows existed. The owner is authoritative either way.
        workspace = self.workspace_repository.get_by_owner(
            current_user_id,
        )

        if workspace is None:
            raise NotFoundError(
                "You don't belong to any workspace."
            )

        return WorkspaceContext(
            workspace=workspace,
            membership=None,
            role=WorkspaceRole.OWNER,
        )

    def get_active_membership(
        self,
        user_id: UUID,
    ) -> WorkspaceMember | None:
        return self.repository.get_active_membership(user_id)

    # ------------------------------------------------------------------
    # Membership creation
    # ------------------------------------------------------------------

    def create_owner(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> WorkspaceMember:
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=WorkspaceRole.OWNER,
            status=WorkspaceMemberStatus.ACTIVE,
        )

        return self.repository.create(member)

    def activate_member(
        self,
        workspace_id: UUID,
        user_id: UUID,
        role: WorkspaceRole,
    ) -> WorkspaceMember:
        """
        Creates the membership, or re-activates the existing row.

        (workspace_id, user_id) is unique, so a user who was
        removed and later re-invited must reuse their row.
        """
        existing = self.repository.get_by_workspace_and_user(
            workspace_id,
            user_id,
        )

        if existing is None:
            member = WorkspaceMember(
                workspace_id=workspace_id,
                user_id=user_id,
                role=role,
                status=WorkspaceMemberStatus.ACTIVE,
            )

            return self.repository.create(member)

        if existing.status == WorkspaceMemberStatus.ACTIVE:
            raise ConflictError(
                "This user is already a member of this workspace."
            )

        existing.role = role
        existing.status = WorkspaceMemberStatus.ACTIVE
        existing.deleted_at = None

        return self.repository.save(existing)

    # ------------------------------------------------------------------
    # Member management
    # ------------------------------------------------------------------

    def list_members(
        self,
        current_user_id: UUID,
    ) -> list[WorkspaceMember]:
        context = self.resolve_context(current_user_id)
        context.require(WorkspacePermission.VIEW_MEMBERS)

        return self.repository.get_by_workspace(
            context.workspace_id,
        )

    def remove_member(
        self,
        current_user_id: UUID,
        member_id: UUID,
    ) -> WorkspaceMember:
        context = self.resolve_context(current_user_id)
        context.require(WorkspacePermission.REMOVE_MEMBERS)

        member = self._get_target(context, member_id)

        if member.user_id == current_user_id:
            raise ConflictError(
                "Use leave workspace to remove yourself."
            )

        if not can_remove_member(context.role, member.role):
            raise PermissionDeniedError(
                "You don't have permission to remove this member."
            )

        member.status = WorkspaceMemberStatus.REMOVED

        return self.repository.save(member)

    def leave_workspace(
        self,
        current_user_id: UUID,
    ) -> WorkspaceMember:
        context = self.resolve_context(current_user_id)

        if context.role == WorkspaceRole.OWNER:
            raise ConflictError(
                "Transfer ownership before leaving the workspace."
            )

        context.require(WorkspacePermission.LEAVE_WORKSPACE)

        if context.membership is None:
            raise NotFoundError("Membership not found.")

        context.membership.status = WorkspaceMemberStatus.REMOVED

        return self.repository.save(context.membership)

    def change_member_role(
        self,
        current_user_id: UUID,
        member_id: UUID,
        new_role: WorkspaceRole,
    ) -> WorkspaceMember:
        context = self.resolve_context(current_user_id)
        context.require(WorkspacePermission.CHANGE_ROLES)

        member = self._get_target(context, member_id)

        if member.user_id == current_user_id:
            raise ConflictError(
                "You cannot change your own role."
            )

        if member.role == new_role:
            raise ConflictError(
                f"This member is already {new_role.value}."
            )

        if not can_change_role(context.role, member.role, new_role):
            raise PermissionDeniedError(
                "You don't have permission to make this role change."
            )

        member.role = new_role

        return self.repository.save(member)

    def transfer_ownership(
        self,
        current_user_id: UUID,
        member_id: UUID,
    ) -> WorkspaceMember:
        context = self.resolve_context(current_user_id)
        context.require(WorkspacePermission.TRANSFER_OWNERSHIP)

        member = self._get_target(context, member_id)

        if member.user_id == current_user_id:
            raise ConflictError(
                "You already own this workspace."
            )

        current_owner = context.membership

        if current_owner is None:
            current_owner = self.create_owner(
                workspace_id=context.workspace_id,
                user_id=current_user_id,
            )

        # All three rows change together.
        member.role = WorkspaceRole.OWNER
        current_owner.role = WorkspaceRole.ADMIN
        context.workspace.owner_user_id = member.user_id

        self.repository.add(member)
        self.repository.add(current_owner)
        self.workspace_repository.add(context.workspace)
        self.repository.commit()

        self.repository.db.refresh(member)

        return member

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_target(
        self,
        context: WorkspaceContext,
        member_id: UUID,
    ) -> WorkspaceMember:
        member = self.repository.get_by_id(member_id)

        if (
            member is None
            or member.workspace_id != context.workspace_id
            or member.status != WorkspaceMemberStatus.ACTIVE
        ):
            raise NotFoundError("Member not found.")

        return member
