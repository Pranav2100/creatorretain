import smtplib
from email.message import EmailMessage as MimeMessage

from app.core.settings import settings
from app.services.email.base import EmailMessage, EmailSender


class SmtpEmailSender(EmailSender):
    """
    Plain SMTP, which covers both ends of the range: a local catcher
    such as Mailpit during development, and most hosted providers in
    production, since nearly all of them accept SMTP.
    """

    def send(self, message: EmailMessage) -> None:
        mime = MimeMessage()

        mime["From"] = (
            f"{settings.EMAIL_FROM_NAME} "
            f"<{settings.EMAIL_FROM_ADDRESS}>"
        )
        mime["To"] = message.to
        mime["Subject"] = message.subject

        mime.set_content(message.text_body)
        mime.add_alternative(message.html_body, subtype="html")

        with smtplib.SMTP(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
        ) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()

            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                server.login(
                    settings.SMTP_USERNAME,
                    settings.SMTP_PASSWORD,
                )

            server.send_message(mime)
