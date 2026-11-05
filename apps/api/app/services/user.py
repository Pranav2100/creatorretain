from app.core.password import hash_password, verify_password
from app.core.security import create_access_token
from app.database.models.user import User
from app.database.repositories.user import UserRepository
from app.services.notification import NotificationService
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UpdateMeRequest,
)


class UserService:
    def __init__(
        self,
        repository: UserRepository,
        notifications: "NotificationService | None" = None,
    ):
        self.repository = repository
        self.notifications = notifications

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

        return LoginResponse(
            access_token=self._token(user),
        )

    # ------------------------------------------------------------------
    # Your own account
    # ------------------------------------------------------------------

    def update_me(
        self,
        user: User,
        request: UpdateMeRequest,
    ) -> User:
        """
        Changes a name, or the address this person signs in with.

        Only what was sent is touched. Changing the email asks for
        the password first: an email address is how an account is
        recovered, so whoever can change it can keep the account,
        and a borrowed session should not be enough on its own.
        """
        if request.first_name is not None:
            user.first_name = request.first_name.strip()

        if request.last_name is not None:
            user.last_name = request.last_name.strip()

        if request.phone is not None:
            user.phone = request.phone.strip() or None

        if request.job_title is not None:
            user.job_title = request.job_title.strip() or None

        # Switches, not text: `is not None` rather than a falsy
        # check, or turning one off would read as not sending it.
        if request.notify_retainers is not None:
            user.notify_retainers = request.notify_retainers

        if request.notify_messages is not None:
            user.notify_messages = request.notify_messages

        if request.notify_work is not None:
            user.notify_work = request.notify_work

        wants = (request.email or "").strip().lower()

        if wants and wants != user.email.lower():
            if not request.current_password:
                raise ValueError(
                    "Enter your password to change your email."
                )

            if not verify_password(
                request.current_password, user.password_hash
            ):
                raise ValueError("That password is not right.")

            taken = self.repository.get_by_email(wants)

            if taken is not None and taken.id != user.id:
                raise ValueError("That email is already in use.")

            user.email = wants

            # Not proven yet, whatever was true of the old one.
            # There is no verification flow today, and leaving
            # this true would be a claim nobody checked.
            user.email_verified = False

        return self.repository.save(user)

    def change_password(
        self,
        user: User,
        request: ChangePasswordRequest,
    ) -> str:
        """
        Sets a new password, ends every session, and returns a
        token for this one.

        The current password is required even though the caller
        is already signed in, because "signed in" and "is the
        owner of this account" are not the same thing - a
        borrowed laptop satisfies the first and not the second.
        """
        if request.new_password != request.confirm_password:
            raise ValueError("The new passwords do not match.")

        if not verify_password(
            request.current_password, user.password_hash
        ):
            raise ValueError("That password is not right.")

        if request.new_password == request.current_password:
            raise ValueError(
                "That is the password you already have."
            )

        user.password_hash = hash_password(request.new_password)

        # Every token minted before this moment stops working,
        # which is the point: if the password is being changed
        # because someone else had it, they had a session too.
        user.token_version += 1

        # Queued before the save, because save() commits - a row
        # added after it is flushed into a transaction that
        # nothing ever commits, and is silently gone when the
        # session closes. Here it lands in the same commit as the
        # password itself, so either both happened or neither.
        #
        # Not optional, either: this is the one email a person
        # cannot turn off, because if it was not them who changed
        # the password it is the only warning they get.
        if self.notifications is not None:
            self.notifications.about_password_change(user)

        saved = self.repository.save(user)

        return self._token(saved)

    @staticmethod
    def _token(user: User) -> str:
        return create_access_token(
            user_id=str(user.id),
            email=user.email,
            token_version=user.token_version,
        )