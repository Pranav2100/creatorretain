from fastapi import APIRouter

from app.core.hash import hash_password
from app.core.security import validate_password
from app.schemas.auth import RegisterRequest

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post("/register")
def register(request: RegisterRequest):

    validate_password(
        request.password,
        request.confirm_password,
    )

    hashed_password = hash_password(request.password)

    return {
        "message": "Registration request received successfully.",
        "email": request.email,
        "hashed_password": hashed_password,
    }