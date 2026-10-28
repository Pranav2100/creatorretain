from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_pulse_service
from app.api.errors import http_error
from app.database.models.user import User
from app.schemas.pulse import PulseResponse
from app.services.pulse import PulseService, Watchable

router = APIRouter(tags=["Pulse"])


@router.get(
    "/pulse",
    response_model=PulseResponse,
    summary="Whether anything a page is showing has changed",
)
def read_pulse(
    scope: list[Watchable] = Query(
        default=[Watchable.RETAINERS],
        description="Repeat for several. What the page is showing.",
    ),
    retainer: UUID | None = Query(
        default=None,
        description="Narrows 'retainers' to one of them.",
    ),
    creator: UUID | None = Query(
        default=None,
        description="Which creator, for the 'creator' scope.",
    ),
    current_user: User = Depends(get_current_user),
    service: PulseService = Depends(get_pulse_service),
):
    """
    Answers in two numbers, and is meant to be asked often.

    A page sends what it is showing and compares the answer with
    the one it was rendered from. When they differ it asks the
    server to render it again - so there is exactly one place the
    page's content comes from, and this is not it.
    """
    try:
        latest, count = service.read(
            current_user.id,
            scope,
            retainer_id=retainer,
            creator_workspace_id=creator,
        )

        return PulseResponse(latest=latest, count=count)

    except ValueError as e:
        raise http_error(e)
