from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_retainer_service
from app.api.errors import http_error
from app.common.enums import RetainerStatus
from app.database.models.user import User
from app.schemas.retainer import (
    AssigneeListResponse,
    Assignee,
    AssignRequest,
    ChangeRequestBody,
    CreateRetainerRequest,
    DeclineRequest,
    DeliverableResponse,
    EndRetainerRequest,
    EventListResponse,
    EventResponse,
    PauseRequest,
    PeriodListResponse,
    PeriodResponse,
    RetainerDetail,
    RetainerListResponse,
    RetainerSummary,
    ReviewDeliverableRequest,
    SubmitDeliverableRequest,
)
from app.services.retainer import RetainerService

router = APIRouter(
    prefix="/retainers",
    tags=["Retainers"],
)

PLAN_OR_PERMISSION = {
    402: {"description": "The plan does not include this"},
    403: {"description": "The role does not permit this"},
}


# ----------------------------------------------------------------------
# The agreement
# ----------------------------------------------------------------------


@router.post(
    "",
    response_model=RetainerDetail,
    status_code=status.HTTP_201_CREATED,
    responses=PLAN_OR_PERMISSION,
    summary="Offer a retainer to a creator",
)
def create_retainer(
    payload: CreateRetainerRequest,
    current_user: User = Depends(get_current_user),
    service: RetainerService = Depends(get_retainer_service),
):
    try:
        retainer = service.create(
            current_user.id,
            creator_workspace_id=payload.creator_workspace_id,
            title=payload.title,
            monthly_amount=payload.monthly_amount,
            deliverables=[
                (spec.deliverable_type, spec.quantity, spec.notes)
                for spec in payload.deliverables
            ],
            start_date=payload.start_date,
            end_date=payload.end_date,
            notice_period_days=payload.notice_period_days,
            terms=payload.terms,
            message=payload.message,
            currency=payload.currency.upper(),
        )

        return RetainerDetail.from_retainer(
            retainer,
            "brand",
            service.clock(),
        )

    except ValueError as e:
        raise http_error(e)


@router.get(
    "",
    response_model=RetainerListResponse,
    summary="Every retainer this workspace is part of",
)
def list_retainers(
    status_filter: list[RetainerStatus] | None = Query(
        default=None,
        alias="status",
        description="Repeat for several.",
    ),
    current_user: User = Depends(get_current_user),
    service: RetainerService = Depends(get_retainer_service),
):
    try:
        retainers, workspace_id = service.list_for_user(
            current_user.id,
            status_filter,
        )

        return RetainerListResponse(
            retainers=[
                RetainerSummary.from_retainer(
                    r,
                    workspace_id,
                    service.clock(),
                )
                for r in retainers
            ],
            total=len(retainers),
        )

    except ValueError as e:
        raise http_error(e)


@router.get(
    "/{retainer_id}",
    response_model=RetainerDetail,
    responses={404: {"description": "Not found"}},
    summary="One retainer, with every period so far",
)
def get_retainer(
    retainer_id: UUID,
    current_user: User = Depends(get_current_user),
    service: RetainerService = Depends(get_retainer_service),
):
    try:
        retainer, side = service.get(current_user.id, retainer_id)

        return RetainerDetail.from_retainer(
        retainer,
        side,
        service.clock(),
    )

    except ValueError as e:
        raise http_error(e)


@router.get(
    "/{retainer_id}/assignees",
    response_model=AssigneeListResponse,
    summary="Who runs this account",
)
def list_assignees(
    retainer_id: UUID,
    current_user: User = Depends(get_current_user),
    service: RetainerService = Depends(get_retainer_service),
):
    try:
        people = service.assignees(current_user.id, retainer_id)

        return AssigneeListResponse(
            assignees=[
                Assignee.from_assignment(a) for a in people
            ],
            total=len(people),
        )

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/{retainer_id}/assignees",
    response_model=AssigneeListResponse,
    responses=PLAN_OR_PERMISSION,
    summary="Put someone on this account",
)
def add_assignee(
    retainer_id: UUID,
    payload: AssignRequest,
    current_user: User = Depends(get_current_user),
    service: RetainerService = Depends(get_retainer_service),
):
    try:
        people = service.assign(
            current_user.id,
            retainer_id,
            payload.user_id,
        )

        return AssigneeListResponse(
            assignees=[
                Assignee.from_assignment(a) for a in people
            ],
            total=len(people),
        )

    except ValueError as e:
        raise http_error(e)


@router.delete(
    "/{retainer_id}/assignees/{user_id}",
    response_model=AssigneeListResponse,
    responses=PLAN_OR_PERMISSION,
    summary="Take someone off this account",
)
def remove_assignee(
    retainer_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    service: RetainerService = Depends(get_retainer_service),
):
    try:
        people = service.unassign(
            current_user.id,
            retainer_id,
            user_id,
        )

        return AssigneeListResponse(
            assignees=[
                Assignee.from_assignment(a) for a in people
            ],
            total=len(people),
        )

    except ValueError as e:
        raise http_error(e)


@router.get(
    "/{retainer_id}/history",
    response_model=EventListResponse,
    summary="Everything that has happened to this retainer",
)
def list_history(
    retainer_id: UUID,
    current_user: User = Depends(get_current_user),
    service: RetainerService = Depends(get_retainer_service),
):
    try:
        events, side = service.history(current_user.id, retainer_id)

        return EventListResponse(
            events=[
                EventResponse.from_event(event, side)
                for event in events
            ],
            total=len(events),
        )

    except ValueError as e:
        raise http_error(e)


@router.get(
    "/{retainer_id}/periods",
    response_model=PeriodListResponse,
    summary="The months this retainer has produced",
)
def list_periods(
    retainer_id: UUID,
    current_user: User = Depends(get_current_user),
    service: RetainerService = Depends(get_retainer_service),
):
    try:
        periods = service.periods(current_user.id, retainer_id)
        today = service.clock()

        return PeriodListResponse(
            periods=[
                PeriodResponse.from_period(period, today)
                for period in periods
            ],
            total=len(periods),
        )

    except ValueError as e:
        raise http_error(e)


# ----------------------------------------------------------------------
# Answering an offer
# ----------------------------------------------------------------------


@router.post(
    "/{retainer_id}/accept",
    response_model=RetainerDetail,
    responses=PLAN_OR_PERMISSION,
    summary="Creator accepts the offer",
)
def accept_retainer(
    retainer_id: UUID,
    current_user: User = Depends(get_current_user),
    service: RetainerService = Depends(get_retainer_service),
):
    try:
        retainer = service.accept(current_user.id, retainer_id)

        return RetainerDetail.from_retainer(
            retainer,
            "creator",
            service.clock(),
        )

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/{retainer_id}/decline",
    response_model=RetainerDetail,
    responses=PLAN_OR_PERMISSION,
    summary="Creator declines the offer",
)
def decline_retainer(
    retainer_id: UUID,
    payload: DeclineRequest | None = None,
    current_user: User = Depends(get_current_user),
    service: RetainerService = Depends(get_retainer_service),
):
    try:
        retainer = service.decline(
            current_user.id,
            retainer_id,
            reason=payload.reason if payload else None,
        )

        return RetainerDetail.from_retainer(
            retainer,
            "creator",
            service.clock(),
        )

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/{retainer_id}/cancel",
    response_model=RetainerDetail,
    responses=PLAN_OR_PERMISSION,
    summary="Brand withdraws an unanswered offer",
)
def cancel_retainer(
    retainer_id: UUID,
    current_user: User = Depends(get_current_user),
    service: RetainerService = Depends(get_retainer_service),
):
    try:
        retainer = service.cancel(current_user.id, retainer_id)

        return RetainerDetail.from_retainer(
            retainer,
            "brand",
            service.clock(),
        )

    except ValueError as e:
        raise http_error(e)


# ----------------------------------------------------------------------
# Running it
# ----------------------------------------------------------------------


@router.post(
    "/{retainer_id}/requests",
    response_model=RetainerDetail,
    responses=PLAN_OR_PERMISSION,
    summary="Ask the other side to pause or resume",
)
def request_change(
    retainer_id: UUID,
    payload: ChangeRequestBody,
    current_user: User = Depends(get_current_user),
    service: RetainerService = Depends(get_retainer_service),
):
    try:
        service.request_change(
            current_user.id,
            retainer_id,
            action=payload.action,
            reason=payload.reason,
        )

        return _detail(service, current_user.id, retainer_id)

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/{retainer_id}/requests/approve",
    response_model=RetainerDetail,
    responses=PLAN_OR_PERMISSION,
    summary="Agree to what the other side asked for",
)
def approve_change(
    retainer_id: UUID,
    current_user: User = Depends(get_current_user),
    service: RetainerService = Depends(get_retainer_service),
):
    try:
        service.approve_change(current_user.id, retainer_id)

        return _detail(service, current_user.id, retainer_id)

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/{retainer_id}/requests/reject",
    response_model=RetainerDetail,
    responses=PLAN_OR_PERMISSION,
    summary="Say no to what the other side asked for",
)
def reject_change(
    retainer_id: UUID,
    payload: PauseRequest | None = None,
    current_user: User = Depends(get_current_user),
    service: RetainerService = Depends(get_retainer_service),
):
    try:
        service.reject_change(
            current_user.id,
            retainer_id,
            reason=payload.reason if payload else None,
        )

        return _detail(service, current_user.id, retainer_id)

    except ValueError as e:
        raise http_error(e)


@router.delete(
    "/{retainer_id}/requests",
    response_model=RetainerDetail,
    responses=PLAN_OR_PERMISSION,
    summary="Take back a request you made",
)
def withdraw_change(
    retainer_id: UUID,
    current_user: User = Depends(get_current_user),
    service: RetainerService = Depends(get_retainer_service),
):
    try:
        service.withdraw_change(current_user.id, retainer_id)

        return _detail(service, current_user.id, retainer_id)

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/{retainer_id}/end",
    response_model=RetainerDetail,
    responses=PLAN_OR_PERMISSION,
    summary="End the agreement for good",
)
def end_retainer(
    retainer_id: UUID,
    payload: EndRetainerRequest | None = None,
    current_user: User = Depends(get_current_user),
    service: RetainerService = Depends(get_retainer_service),
):
    try:
        service.end(
            current_user.id,
            retainer_id,
            reason=payload.reason if payload else None,
        )

        return _detail(service, current_user.id, retainer_id)

    except ValueError as e:
        raise http_error(e)


# ----------------------------------------------------------------------
# The work
# ----------------------------------------------------------------------


@router.post(
    "/deliverables/{deliverable_id}/submit",
    response_model=DeliverableResponse,
    responses=PLAN_OR_PERMISSION,
    summary="Creator submits one deliverable",
)
def submit_deliverable(
    deliverable_id: UUID,
    payload: SubmitDeliverableRequest,
    current_user: User = Depends(get_current_user),
    service: RetainerService = Depends(get_retainer_service),
):
    try:
        deliverable = service.submit_deliverable(
            current_user.id,
            deliverable_id,
            url=str(payload.url),
            note=payload.note,
        )

        return DeliverableResponse.model_validate(deliverable)

    except ValueError as e:
        raise http_error(e)


@router.post(
    "/deliverables/{deliverable_id}/review",
    response_model=DeliverableResponse,
    responses=PLAN_OR_PERMISSION,
    summary="Brand approves, asks for a revision, or rejects",
)
def review_deliverable(
    deliverable_id: UUID,
    payload: ReviewDeliverableRequest,
    current_user: User = Depends(get_current_user),
    service: RetainerService = Depends(get_retainer_service),
):
    try:
        deliverable = service.review_deliverable(
            current_user.id,
            deliverable_id,
            decision=payload.decision,
            note=payload.note,
        )

        return DeliverableResponse.model_validate(deliverable)

    except ValueError as e:
        raise http_error(e)


# ----------------------------------------------------------------------
# Internals
# ----------------------------------------------------------------------


def _detail(
    service: RetainerService,
    user_id: UUID,
    retainer_id: UUID,
) -> RetainerDetail:
    retainer, side = service.get(user_id, retainer_id)

    return RetainerDetail.from_retainer(
        retainer,
        side,
        service.clock(),
    )
