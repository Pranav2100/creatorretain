from app.core.password import hash_password
from app.database.models.user import User
from app.database.repositories.user import UserRepository
from app.schemas.auth import RegisterRequest


class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    def register(self, request: RegisterRequest) -> User:
        if self.repository.email_exists(request.email):
            raise ValueError("Email already registered")

        user = User(
            email=request.email,
            password_hash=hash_password(request.password),
            first_name=request.first_name,
            last_name=request.last_name,
            phone=request.phone,
        )

        return self.repository.create(user)