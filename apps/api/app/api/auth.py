from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.repositories.user import UserRepository
from app.database.session import get_db
from app.schemas.auth import RegisterRequest
from app.services.user import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register")
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    service = UserService(UserRepository(db))

    try:
        user = service.register(request)

        return {
            "id": str(user.id),
            "email": user.email,
            "message": "Registration successful",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))