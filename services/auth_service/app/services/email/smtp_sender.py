"""SMTP email transport."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage as MIMEEmailMessage
from email.utils import formataddr

from app.services.email.base import EmailMessage, EmailService

from shared.exceptions.email import EmailDeliveryError
from shared.logging import get_logger

logger = get_logger(__name__)


class SMTPEmailService(EmailService):
    """Delivers email over SMTP with optional STARTTLS and authentication.

    Builds a multipart ``text/plain`` + ``text/html`` message so clients that
    cannot render HTML still receive a readable fallback. Any transport-level
    failure is normalised to :class:`EmailDeliveryError`.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int,
        from_address: str,
        from_name: str,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
        timeout_seconds: int = 10,
    ) -> None:
        self._host = host
        self._port = port
        self._from_address = from_address
        self._from_name = from_name
        self._username = username
        self._password = password
        self._use_tls = use_tls
        self._timeout = timeout_seconds

    def _build_mime_message(self, message: EmailMessage) -> MIMEEmailMessage:
        mime = MIMEEmailMessage()
        mime["Subject"] = message.subject
        mime["From"] = formataddr((self._from_name, self._from_address))
        mime["To"] = message.to_email
        # A plain-text part is always set first; the HTML part is added as an
        # alternative so compliant clients prefer it.
        mime.set_content(message.text_body or message.subject)
        mime.add_alternative(message.html_body, subtype="html")
        return mime

    def send_email(self, message: EmailMessage) -> None:
        """Dispatch ``message`` over SMTP."""
        mime = self._build_mime_message(message)
        try:
            with smtplib.SMTP(
                host=self._host,
                port=self._port,
                timeout=self._timeout,
            ) as server:
                if self._use_tls:
                    server.starttls()
                if self._username and self._password:
                    server.login(self._username, self._password)
                server.send_message(mime)
        except (smtplib.SMTPException, OSError) as exc:
            # Never include the message body: it carries the verification link.
            logger.error(
                "SMTP delivery failed to=%s subject=%s: %s",
                message.to_email,
                message.subject,
                exc,
            )
            raise EmailDeliveryError("Failed to send email.") from exc

        logger.info(
            "SMTP email dispatched to=%s subject=%s",
            message.to_email,
            message.subject,
        )
