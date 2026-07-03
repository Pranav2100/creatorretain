from app.core.password import hash_password, verify_password
from app.core.security import create_access_token
from app.database.models.user import User
from app.database.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest


class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    def register(self, request: RegisterRequest) -> User:
        if request.password != request.confirm_password:
            raise ValueError("Passwords do not match")

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

    def login(self, request: LoginRequest) -> LoginResponse:
        user = self.repository.get_by_email(request.email)

        if user is None:
            raise ValueError("Invalid email or password")

        if not verify_password(request.password, user.password_hash):
            raise ValueError("Invalid email or password")

        token = create_access_token(
            user_id=str(user.id),
            email=user.email,
        )

        return LoginResponse(
            access_token=token,
        )