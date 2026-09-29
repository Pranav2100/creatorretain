from fastapi import HTTPException, status

from app.common.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    PlanLimitError,
)


def http_error(error: ValueError) -> HTTPException:
    """
    Translates a domain error into the matching HTTP response.

    Plain ValueError keeps the existing 400 behaviour so that
    older services are unaffected.
    """
    if isinstance(error, NotFoundError):
        code = status.HTTP_404_NOT_FOUND

    elif isinstance(error, PermissionDeniedError):
        code = status.HTTP_403_FORBIDDEN

    elif isinstance(error, PlanLimitError):
        # 402 rather than 403: the block is the plan, not the person,
        # so the interface should offer an upgrade rather than say no.
        code = status.HTTP_402_PAYMENT_REQUIRED

    elif isinstance(error, ConflictError):
        code = status.HTTP_409_CONFLICT

    else:
        code = status.HTTP_400_BAD_REQUEST

    return HTTPException(
        status_code=code,
        detail=str(error),
    )
