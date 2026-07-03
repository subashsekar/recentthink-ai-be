"""Console email transport for local development and tests."""

from __future__ import annotations

from app.services.email.base import EmailMessage, EmailService

from shared.logging import get_logger

logger = get_logger(__name__)


class ConsoleEmailService(EmailService):
    """Writes emails to the application log instead of sending them.

    This is the default transport for local development and the test suite so
    no external mail server is contacted. The recipient and subject are logged
    at INFO; the rendered body (which contains the verification link) is logged
    at DEBUG only, as a developer convenience for this fake transport.
    """

    def __init__(self, *, from_address: str, from_name: str) -> None:
        self._from_address = from_address
        self._from_name = from_name

    def send_email(self, message: EmailMessage) -> None:
        """Log the email in lieu of delivering it."""
        logger.info(
            "Console email dispatched from=%s <%s> to=%s subject=%s",
            self._from_name,
            self._from_address,
            message.to_email,
            message.subject,
        )
        logger.debug(
            "Console email body to=%s:\n%s",
            message.to_email,
            message.text_body or message.html_body,
        )
