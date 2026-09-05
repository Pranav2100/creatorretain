from app.core.settings import settings
from app.services.email.base import EmailMessage, EmailSender
from app.services.email.console import ConsoleEmailSender
from app.services.email.smtp import SmtpEmailSender

__all__ = [
    "EmailMessage",
    "EmailSender",
    "ConsoleEmailSender",
    "SmtpEmailSender",
    "get_email_sender",
]

_BACKENDS: dict[str, type[EmailSender]] = {
    "console": ConsoleEmailSender,
    "smtp": SmtpEmailSender,
}


def get_email_sender() -> EmailSender:
    backend = _BACKENDS.get(settings.EMAIL_BACKEND.lower())

    if backend is None:
        raise ValueError(
            f"Unknown EMAIL_BACKEND '{settings.EMAIL_BACKEND}'. "
            f"Expected one of: {', '.join(_BACKENDS)}."
        )

    return backend()
