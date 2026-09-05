import logging

from app.services.email.base import EmailMessage, EmailSender

logger = logging.getLogger("app.email")


class ConsoleEmailSender(EmailSender):
    """
    Writes the email to the log instead of sending it.

    The default in development: the whole invitation flow can be
    exercised end to end with no provider, no domain and no keys.
    """

    def send(self, message: EmailMessage) -> None:
        logger.info(
            "\n"
            "----- email -----\n"
            "To:      %s\n"
            "Subject: %s\n"
            "\n"
            "%s\n"
            "----- end -----",
            message.to,
            message.subject,
            message.text_body,
        )
