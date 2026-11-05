from dataclasses import dataclass
from uuid import UUID

from app.common.entitlements import (
    Capability,
    PlanLimits,
    capabilities_for,
    has_capability,
    limits_for,
    upgrade_message,
)
from app.common.enums import (
    WorkspaceMemberStatus,
    WorkspacePlan,
    WorkspaceRole,
)
from app.common.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    PlanLimitError,
)
from app.common.permissions import (
    WorkspacePermission,
    can_change_role,
    can_remove_member,
    permissions_for,
)
from app.database.models.workspace import Workspace
from app.database.models.workspace_member import WorkspaceMember
from app.database.repositories.custom_role import (
    CustomRoleRepository,
)
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

    Carries the workspace's plan too, so a service can ask both
    questions from one object: may this person do it (role), and
    may this workspace do it at all (plan).
    """

    workspace: Workspace
    membership: WorkspaceMember | None
    role: WorkspaceRole

    # Everything the person's custom roles add on top of the
    # built-in one. Empty for almost everybody: a workspace has
    # none of these until it invents some.
    #
    # Resolved once, when the context is built, rather than
    # looked up at each check - a single request asks "may they"
    # several times, and the answer must not change halfway
    # through because somebody edited a role in between.
    granted: frozenset[WorkspacePermission] = frozenset()

    @property
    def workspace_id(self) -> UUID:
        return self.workspace.id

    @property
    def plan(self) -> WorkspacePlan:
        return self.workspace.effective_plan

    @property
    def capabilities(self) -> frozenset[Capability]:
        return capabilities_for(
            self.workspace.workspace_type,
            self.plan,
        )

    @property
    def limits(self) -> PlanLimits:
        return limits_for(
            self.workspace.workspace_type,
            self.plan,
        )

    @property
    def permissions(self) -> frozenset[WorkspacePermission]:
        """
        Everything this person can do here.

        The built-in role sets the floor and custom roles add to
        it; nothing subtracts. Every permission question in the
        application comes through here, which is what made custom
        roles a change to one class rather than a sweep through
        every service.
        """
        return permissions_for(self.role) | self.granted

    def require(
        self,
        permission: WorkspacePermission,
        message: str | None = None,
    ) -> None:
        if permission not in self.permissions:
            raise PermissionDeniedError(
                message
                or "You don't have permission to perform this action."
            )

    def allows(self, permission: WorkspacePermission) -> bool:
        """
        The same question as `require`, asked without raising.

        For the places that branch on a permission rather than
        refuse on it - narrowing a list to what this person runs,
        say, instead of turning them away from the page.
        """
        return permission in self.permissions

    def can(self, capability: Capability) -> bool:
        return has_capability(
            self.workspace.workspace_type,
            self.plan,
            capability,
        )

    def require_capability(self, capability: Capability) -> None:
        """
        Plan gate. Raises with the tier that would unlock it, so the
        caller can say what to do rather than only what went wrong.
        """
        if not self.can(capability):
            raise PlanLimitError(upgrade_message(capability))

    def require_within_limit(
        self,
        limit_name: str,
        current: int,
        noun: str,
    ) -> None:
        """
        Numeric gate. `current` is what already exists; this refuses
        when adding one more would pass the ceiling.
        """
        ceiling = getattr(self.limits, limit_name, None)

        if ceiling is None:
            return

        if current < ceiling:
            return

        if ceiling == 0:
            raise PlanLimitError(
                f"Your plan does not include {noun}. Upgrade to add them."
            )

        raise PlanLimitError(
            f"Your plan allows {ceiling} {noun}. "
            "Upgrade to add more."
        )


class WorkspaceMemberService:
    def __init__(
        self,
        repository: WorkspaceMemberRepository,
        workspace_repository: WorkspaceRepository,
        # Optional so anything constructing this service without
        # knowing about custom roles still works - it just
        # resolves a context with none of them, which is what
        # every workspace has until it invents one.
        custom_role_repository: "CustomRoleRepository | None" = None,
    ):
        self.repository = repository
        self.workspace_repository = workspace_repository
        self.custom_role_repository = custom_role_repository

    # ------------------------------------------------------------------
    # Workspace resolution
    # ------------------------------------------------------------------

    def _granted_to(
        self,
        member_id: UUID,
    ) -> frozenset[WorkspacePermission]:
        """
        Everything this member's custom roles add.

        The Owner fallback below does not go through here: it has
        no membership row to hang grants off, and the Owner holds
        everything a custom role could add anyway.
        """
        if self.custom_role_repository is None:
            return frozenset()

        granted: set[WorkspacePermission] = set()

        for role in self.custom_role_repository.roles_for_member(
            member_id,
        ):
            granted |= role.granted

        return frozenset(granted)

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
                granted=self._granted_to(membership.id),
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
