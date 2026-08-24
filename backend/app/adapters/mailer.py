import base64
import smtplib
from email.message import EmailMessage

from app.adapters.base import Mailer, SentMessage
from app.adapters.google.session import google_call
from app.core.config import settings
from app.models.api_usage_log import ApiName
from app.models.recruiter import Recruiter

GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"

# smtplib.SMTP has no default timeout — an unreachable Mailhog would otherwise
# hang the Celery worker until soft_time_limit fires instead of failing fast
# into the retryable path.
_SMTP_TIMEOUT_SECONDS = 10


class LocalMailer:
    def send(self, recruiter: Recruiter, *, to: str, subject: str, body: str) -> SentMessage:
        message = EmailMessage()
        message["From"] = recruiter.email
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        with smtplib.SMTP(
            settings.smtp_host, settings.smtp_port, timeout=_SMTP_TIMEOUT_SECONDS
        ) as smtp:
            smtp.send_message(message)
        return SentMessage()


class GmailMailer:
    def send(self, recruiter: Recruiter, *, to: str, subject: str, body: str) -> SentMessage:
        message = EmailMessage()
        message["From"] = recruiter.email
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        response = google_call(
            recruiter, ApiName.GOOGLE_GMAIL, "POST", GMAIL_SEND_URL, json={"raw": raw}
        )
        data = response.json()
        return SentMessage(message_id=data.get("id"), thread_id=data.get("threadId"))


def get_mailer() -> Mailer:
    if settings.mailer == "local":
        return LocalMailer()
    return GmailMailer()
