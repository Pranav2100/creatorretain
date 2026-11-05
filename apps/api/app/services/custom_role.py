from uuid import UUID

from app.common.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.common.permissions import (
    WorkspacePermission,
    can_define_roles,
    can_grant_role,
    can_shape_role,
)
from app.database.models.workspace_custom_role import (
    MAX_ROLE_NAME_LENGTH,
    MAX_ROLES_PER_WORKSPACE,
    WorkspaceCustomRole,
)
from app.database.repositories.custom_role import (
    CustomRoleRepository,
)
from app.database.repositories.workspace_member import (
    WorkspaceMemberRepository,
)
from app.services.workspace_member import WorkspaceContext


class CustomRoleService:
    """
    Roles a workspace invented, and who holds them.

    Every method here answers the same two questions in the same
    order: may this person touch roles at all, and is what they
    are asking for within what they themselves hold. The second
    is the one that matters - it is what makes it impossible to
    end up with a permission you could not already hand out by
    hand, and it is checked against the actor's *effective*
    permissions, so somebody who got CHANGE_ROLES through a
    custom role is bound by exactly the same ceiling as an Admin.
    """

    def __init__(
        self,
        repository: CustomRoleRepository,
        member_repository: WorkspaceMemberRepository,
    ):
        self.repository = repository
        self.member_repository = member_repository

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def list_roles(
        self,
        context: WorkspaceContext,
    ) -> list[WorkspaceCustomRole]:
        context.require(
            WorkspacePermission.VIEW_MEMBERS,
            "You don't have permission to see this workspace's roles.",
        )

        return self.repository.list_for_workspace(context.workspace_id)

    def roles_by_user(
        self,
        context: WorkspaceContext,
    ) -> dict[UUID, list[WorkspaceCustomRole]]:
        context.require(WorkspacePermission.VIEW_MEMBERS)

        return self.repository.roles_by_user(context.workspace_id)

    def granted_to(
        self,
        member_id: UUID,
    ) -> frozenset[WorkspacePermission]:
        """
        What this member's custom roles add up to.

        Deliberately ungated: this is what builds the context that
        every other permission check reads, so asking it to check
        a permission first would be circular.
        """
        granted: set[WorkspacePermission] = set()

        for role in self.repository.roles_for_member(member_id):
            granted |= role.granted

        return frozenset(granted)

    # ------------------------------------------------------------------
    # Defining
    # ------------------------------------------------------------------

    def _require_definer(self, context: WorkspaceContext) -> None:
        if not can_define_roles(context.permissions):
            raise PermissionDeniedError(
                "You don't have permission to manage roles."
            )

    def _clean_name(self, name: str) -> str:
        cleaned = " ".join(name.split())

        if not cleaned:
            raise ConflictError("Give the role a name.")

        if len(cleaned) > MAX_ROLE_NAME_LENGTH:
            raise ConflictError(
                f"A role name can be at most "
                f"{MAX_ROLE_NAME_LENGTH} characters."
            )

        return cleaned

    def _clean_permissions(
        self,
        wanted: list[str],
    ) -> frozenset[WorkspacePermission]:
        known = {p.value for p in WorkspacePermission}
        unknown = sorted(set(wanted) - known)

        if unknown:
            raise ConflictError(
                f"Not a permission: {', '.join(unknown)}."
            )

        chosen = frozenset(WorkspacePermission(v) for v in wanted)

        if not chosen:
            raise ConflictError(
                "A role has to grant at least one thing."
            )

        return chosen

    def create_role(
        self,
        context: WorkspaceContext,
        name: str,
        permissions: list[str],
    ) -> WorkspaceCustomRole:
        self._require_definer(context)

        cleaned = self._clean_name(name)
        chosen = self._clean_permissions(permissions)

        if not can_shape_role(context.permissions, chosen):
            raise PermissionDeniedError(
                "A role cannot grant something you do not have "
                "yourself."
            )

        if self.repository.get_by_name(
            context.workspace_id,
            cleaned,
        ):
            raise ConflictError(
                f"There is already a role called {cleaned}."
            )

        count = self.repository.count_for_workspace(
            context.workspace_id,
        )

        if count >= MAX_ROLES_PER_WORKSPACE:
            raise ConflictError(
                f"A workspace can have at most "
                f"{MAX_ROLES_PER_WORKSPACE} roles."
            )

        return self.repository.create(
            workspace_id=context.workspace_id,
            name=cleaned,
            permissions=sorted(p.value for p in chosen),
            created_by_user_id=self._actor(context),
        )

    def _resolve(
        self,
        context: WorkspaceContext,
        role_id: UUID,
    ) -> WorkspaceCustomRole:
        role = self.repository.get(context.workspace_id, role_id)

        if role is None:
            raise NotFoundError("Role not found.")

        return role

    def update_role(
        self,
        context: WorkspaceContext,
        role_id: UUID,
        name: str | None = None,
        permissions: list[str] | None = None,
    ) -> WorkspaceCustomRole:
        self._require_definer(context)

        role = self._resolve(context, role_id)
        existing = role.granted

        chosen = (
            self._clean_permissions(permissions)
            if permissions is not None
            else existing
        )

        # Both sides checked: what it would grant, and what it
        # already grants. See can_shape_role - editing down a role
        # you could not have built is a way of taking a permission
        # away from other people.
        if not can_shape_role(context.permissions, chosen, existing):
            raise PermissionDeniedError(
                "You can only change a role whose permissions you "
                "hold yourself."
            )

        if name is not None:
            cleaned = self._clean_name(name)
            clash = self.repository.get_by_name(
                context.workspace_id,
                cleaned,
            )

            if clash is not None and clash.id != role.id:
                raise ConflictError(
                    f"There is already a role called {cleaned}."
                )

            role.name = cleaned

        if permissions is not None:
            role.permissions = sorted(p.value for p in chosen)

        self.repository.db.flush()

        return role

    def reorder(
        self,
        context: WorkspaceContext,
        ordered_ids: list[UUID],
    ) -> list[WorkspaceCustomRole]:
        """
        Put the list in this order.

        Position is presentation only, so this needs nothing more
        than permission to manage roles - no subset check, because
        moving a row changes nothing about what anybody can do.
        """
        self._require_definer(context)

        roles = self.repository.list_for_workspace(
            context.workspace_id,
        )
        by_id = {role.id: role for role in roles}

        unknown = [rid for rid in ordered_ids if rid not in by_id]

        if unknown:
            raise NotFoundError("Role not found.")

        if len(set(ordered_ids)) != len(ordered_ids):
            raise ConflictError("A role was listed twice.")

        if len(ordered_ids) != len(roles):
            raise ConflictError(
                "Send the whole list, in the order you want it."
            )

        for position, role_id in enumerate(ordered_ids):
            by_id[role_id].position = position

        self.repository.db.flush()

        return self.repository.list_for_workspace(
            context.workspace_id,
        )

    def delete_role(
        self,
        context: WorkspaceContext,
        role_id: UUID,
    ) -> None:
        self._require_definer(context)

        role = self._resolve(context, role_id)

        if not can_shape_role(
            context.permissions,
            frozenset(),
            role.granted,
        ):
            raise PermissionDeniedError(
                "You can only delete a role whose permissions you "
                "hold yourself."
            )

        self.repository.delete(role)

    # ------------------------------------------------------------------
    # Handing out
    # ------------------------------------------------------------------

    def _member(self, context: WorkspaceContext, user_id: UUID):
        member = self.member_repository.get_by_workspace_and_user(
            context.workspace_id,
            user_id,
        )

        if member is None:
            raise NotFoundError("Member not found.")

        return member

    def grant(
        self,
        context: WorkspaceContext,
        user_id: UUID,
        role_id: UUID,
    ) -> WorkspaceCustomRole:
        self._require_definer(context)

        role = self._resolve(context, role_id)
        member = self._member(context, user_id)

        if not can_grant_role(
            context.role,
            context.permissions,
            member.role,
            role.granted,
        ):
            raise PermissionDeniedError(
                "You can't give this role to this person."
            )

        self.repository.record_grant(
            member_id=member.id,
            role_id=role.id,
            granted_by_user_id=self._actor(context),
        )

        return role

    def revoke(
        self,
        context: WorkspaceContext,
        user_id: UUID,
        role_id: UUID,
    ) -> None:
        self._require_definer(context)

        role = self._resolve(context, role_id)
        member = self._member(context, user_id)

        # Taking a role away is gated the same as giving it. Not
        # because removing a permission is dangerous in itself,
        # but because "who may change this person's access" should
        # not have two different answers depending on direction -
        # otherwise a Manager who cannot promote somebody can
        # still strip them.
        if not can_grant_role(
            context.role,
            context.permissions,
            member.role,
            role.granted,
        ):
            raise PermissionDeniedError(
                "You can't take this role from this person."
            )

        grant = self.repository.get_grant(member.id, role.id)

        if grant is None:
            raise NotFoundError("They don't have that role.")

        self.repository.revoke(grant)

    def _actor(self, context: WorkspaceContext) -> UUID | None:
        return (
            context.membership.user_id
            if context.membership is not None
            else None
        )
