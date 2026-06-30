from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr


class UserRole(str, Enum):
    CREATOR = "creator"
    BRAND = "brand"
    ADMIN = "admin"


class User(BaseModel):
    id: UUID = uuid4()

    first_name: str
    last_name: str

    email: EmailStr

    is_email_verified: bool = False

    role: UserRole | None = None

    is_two_factor_enabled: bool = False

    is_active: bool = True