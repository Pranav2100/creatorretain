from pydantic import BaseModel, EmailStr, Field, field_validator

from app.common.validators import validate_password
from app.schemas.user import UserResponse


def _checked(password: str) -> str:
    """
    The password rules, as a Pydantic validator.

    Left as a ValueError so Pydantic turns it into a 422 with the
    reason attached, rather than a flat "invalid".
    """
    validate_password(password)

    return password


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str
    confirm_password: str
    phone: str | None = None

    _check = field_validator("password")(_checked)


class RegisterResponse(BaseModel):
    message: str
    user: UserResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UpdateMeRequest(BaseModel):
    """
    Your own name, and the address you sign in with.

    Every field is optional and only what is sent is changed, so
    a form that edits one thing need not resend the rest, and
    cannot blank a field by forgetting it.
    """

    first_name: str | None = Field(
        default=None, min_length=1, max_length=100
    )
    last_name: str | None = Field(
        default=None, min_length=1, max_length=100
    )
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    job_title: str | None = Field(default=None, max_length=80)

    # Only needed in order to change the email, because that is
    # the thing someone holding a stolen session would change
    # first - it is how the account is recovered.
    current_password: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

    _check = field_validator("new_password")(_checked)


class ChangePasswordResponse(BaseModel):
    """
    Carries a fresh token, because changing a password ends every
    session - including the one that changed it. Without this the
    person would be signed out of the browser they just used.
    """

    message: str
    access_token: str
    token_type: str = "bearer"
