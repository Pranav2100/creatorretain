from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    confirm_password: str
    phone: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str