from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.common.entitlements import Capability
from app.common.enums import WorkspacePlan, WorkspaceType


class PlanLimitsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    discovery_results: int | None
    active_retainers: int | None
    represented_creators: int | None
    team_members: int | None


class PlanUsageResponse(BaseModel):
    team_members: int
    pending_invitations: int


class WorkspacePlanResponse(BaseModel):
    plan: WorkspacePlan
    configured_plan: WorkspacePlan
    plan_expires_at: datetime | None
    workspace_type: WorkspaceType
    capabilities: list[Capability]
    limits: PlanLimitsResponse
    usage: PlanUsageResponse


class PlanOptionResponse(BaseModel):
    plan: WorkspacePlan
    is_current: bool
    capabilities: list[Capability]
    adds: list[Capability]
    limits: PlanLimitsResponse


class PlanOptionListResponse(BaseModel):
    options: list[PlanOptionResponse]


class ChangePlanRequest(BaseModel):
    plan: WorkspacePlan
