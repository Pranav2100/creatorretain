from uuid import UUID

from app.common.entitlements import (
    Capability,
    PlanLimits,
    capabilities_for,
    is_plan_valid,
    limits_for,
    plans_for_type,
)
from app.common.enums import WorkspacePlan, WorkspaceType
from app.common.exceptions import ConflictError, PermissionDeniedError
from app.common.permissions import WorkspacePermission
from app.core.settings import settings
from app.database.models.workspace import Workspace
from app.database.repositories.workspace import WorkspaceRepository
from app.database.repositories.workspace_invitation import (
    WorkspaceInvitationRepository,
)
from app.database.repositories.workspace_member import (
    WorkspaceMemberRepository,
)
from app.services.workspace_member import WorkspaceMemberService


class WorkspacePlanService:
    """
    Reads and changes the plan a workspace is on.

    Deliberately has no idea what anything costs. When billing
    arrives it writes to the same column from a subscription
    webhook, and the self-serve path below goes away.
    """

    def __init__(
        self,
        workspace_repository: WorkspaceRepository,
        member_repository: WorkspaceMemberRepository,
        invitation_repository: WorkspaceInvitationRepository,
        member_service: WorkspaceMemberService,
    ):
        self.workspace_repository = workspace_repository
        self.member_repository = member_repository
        self.invitation_repository = invitation_repository
        self.member_service = member_service

    def get_plan(self, current_user_id: UUID):
        context = self.member_service.resolve_context(current_user_id)

        return self._describe(context.workspace)

    def available_plans(
        self,
        current_user_id: UUID,
    ) -> list[dict]:
        """
        What this workspace could move to, with what each unlocks -
        enough for an upgrade screen without hard-coding the tiers
        in the frontend.
        """
        context = self.member_service.resolve_context(current_user_id)
        workspace_type = context.workspace.workspace_type
        current = context.plan

        held = capabilities_for(workspace_type, current)

        options = []

        for plan in plans_for_type(workspace_type):
            capabilities = capabilities_for(workspace_type, plan)

            options.append(
                {
                    "plan": plan,
                    "is_current": plan == current,
                    "capabilities": sorted(capabilities),
                    "adds": sorted(capabilities - held),
                    "limits": limits_for(workspace_type, plan),
                }
            )

        return options

    def change_plan(
        self,
        current_user_id: UUID,
        plan: WorkspacePlan,
    ):
        """
        Stand-in for billing. Guarded by a setting so it can be
        switched off the day a payment provider owns this column.
        """
        if not settings.ALLOW_SELF_SERVE_PLAN_CHANGE:
            raise PermissionDeniedError(
                "Plans are changed through billing."
            )

        context = self.member_service.resolve_context(current_user_id)

        # Paying is an owner decision, not a day-to-day admin one.
        context.require(
            WorkspacePermission.MANAGE_BILLING,
            "Only the workspace owner can change the plan. "
            "Ask them to upgrade.",
        )

        workspace = context.workspace

        if not is_plan_valid(workspace.workspace_type, plan):
            raise ConflictError(
                f"{plan.value} is not available for "
                f"{workspace.workspace_type.value} workspaces."
            )

        if workspace.plan == plan:
            raise ConflictError(
                f"This workspace is already on {plan.value}."
            )

        # Downgrading below current usage is refused rather than
        # silently stranding members outside the new ceiling.
        self._guard_downgrade(workspace, plan)

        workspace.plan = plan
        workspace.plan_expires_at = None

        self.workspace_repository.save(workspace)

        return self._describe(workspace)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _usage(self, workspace: Workspace) -> dict[str, int]:
        return {
            "team_members": self.member_repository.count_active(
                workspace.id,
            ),
            "pending_invitations": len(
                self.invitation_repository.get_live_pending_by_workspace(
                    workspace.id,
                )
            ),
        }

    def _guard_downgrade(
        self,
        workspace: Workspace,
        plan: WorkspacePlan,
    ) -> None:
        new_limits = limits_for(workspace.workspace_type, plan)

        if new_limits.team_members is None:
            return

        usage = self._usage(workspace)
        seats = usage["team_members"] + usage["pending_invitations"]

        if seats > new_limits.team_members:
            raise ConflictError(
                f"{plan.value} allows {new_limits.team_members} team "
                f"members and this workspace has {seats}. Remove some "
                "first."
            )

    def _describe(self, workspace: Workspace) -> dict:
        plan = workspace.effective_plan

        return {
            "plan": plan,
            "configured_plan": workspace.plan,
            "plan_expires_at": workspace.plan_expires_at,
            "workspace_type": workspace.workspace_type,
            "capabilities": sorted(
                capabilities_for(workspace.workspace_type, plan),
            ),
            "limits": limits_for(workspace.workspace_type, plan),
            "usage": self._usage(workspace),
        }
