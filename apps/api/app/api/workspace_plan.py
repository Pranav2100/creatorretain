from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_workspace_plan_service
from app.api.errors import http_error
from app.database.models.user import User
from app.schemas.workspace_plan import (
    ChangePlanRequest,
    PlanOptionListResponse,
    PlanOptionResponse,
    WorkspacePlanResponse,
)
from app.services.workspace_plan import WorkspacePlanService

router = APIRouter(
    prefix="/workspace-plan",
    tags=["Workspace Plan"],
)


@router.get(
    "",
    response_model=WorkspacePlanResponse,
)
def get_plan(
    current_user: User = Depends(get_current_user),
    service: WorkspacePlanService = Depends(
        get_workspace_plan_service,
    ),
):
    try:
        return WorkspacePlanResponse(**service.get_plan(current_user.id))

    except ValueError as e:
        raise http_error(e)


@router.get(
    "/options",
    response_model=PlanOptionListResponse,
)
def list_plan_options(
    current_user: User = Depends(get_current_user),
    service: WorkspacePlanService = Depends(
        get_workspace_plan_service,
    ),
):
    try:
        options = service.available_plans(current_user.id)

        return PlanOptionListResponse(
            options=[
                PlanOptionResponse(**option) for option in options
            ]
        )

    except ValueError as e:
        raise http_error(e)


@router.put(
    "",
    response_model=WorkspacePlanResponse,
)
def change_plan(
    request: ChangePlanRequest,
    current_user: User = Depends(get_current_user),
    service: WorkspacePlanService = Depends(
        get_workspace_plan_service,
    ),
):
    """
    Stand-in for billing while there is none. Owner only, and
    switched off with ALLOW_SELF_SERVE_PLAN_CHANGE once a payment
    provider owns this.
    """
    try:
        return WorkspacePlanResponse(
            **service.change_plan(current_user.id, request.plan)
        )

    except ValueError as e:
        raise http_error(e)
