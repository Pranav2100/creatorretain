from fastapi import APIRouter, HTTPException

from app.schemas.auth import RegisterRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register")
def register(request: RegisterRequest):

    if request.password != request.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match.",
        )

    return {
        "message": "Registration request received successfully.",
        "email": request.email,
    }