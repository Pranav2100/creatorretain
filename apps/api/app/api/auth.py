from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.database.models.user import User
from app.database.repositories.user import UserRepository
from app.database.session import get_db
from app.schemas.auth import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    UpdateMeRequest,
)
from app.schemas.user import UserResponse
from app.services.user import UserService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    service = UserService(UserRepository(db))

    try:
        user = service.register(request)

        return RegisterResponse(
            message="Registration successful",
            user=UserResponse.model_validate(user),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/login",
    response_model=LoginResponse,
)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    service = UserService(UserRepository(db))

    try:
        return service.login(request)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.get(
    "/me",
    response_model=UserResponse,
)
def me(
    current_user: User = Depends(get_current_user),
):
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Change your own name, email or phone",
)
def update_me(
    request: UpdateMeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    The person, not the workspace.

    Everything else in this API is about what a workspace is and
    does. This is the one place someone edits themselves, and it
    is why a member of someone else's workspace has a settings
    page worth opening at all.
    """
    service = UserService(UserRepository(db))

    try:
        user = service.update_me(current_user, request)

        return UserResponse.model_validate(user)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
    summary="Change your password and end every other session",
)
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns a new token along with the confirmation.

    Changing a password invalidates every token this user holds,
    this request's included, so without a replacement the person
    would be signed out of the browser they just used - and would
    reasonably wonder whether the change had worked.
    """
    service = UserService(UserRepository(db))

    try:
        token = service.change_password(current_user, request)

        return ChangePasswordResponse(
            message=(
                "Password changed. Other sessions are signed out."
            ),
            access_token=token,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )