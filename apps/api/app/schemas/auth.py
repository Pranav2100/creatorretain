from pydantic import BaseModel, EmailStr

from app.schemas.user import UserResponse


class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    confirm_password: str
    phone: str | None = None


class RegisterResponse(BaseModel):
    message: str
    user: UserResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"