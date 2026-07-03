"""Email delivery subsystem.

Exposes the provider-agnostic :class:`EmailService` interface, its concrete
transports, and the factory that selects one from configuration. Business
logic depends only on the :class:`EmailService` abstraction, so providers can
be added or swapped without changing callers.
"""

from app.services.email.base import EmailMessage, EmailService
from app.services.email.console_sender import ConsoleEmailService
from app.services.email.factory import build_email_service
from app.services.email.smtp_sender import SMTPEmailService

__all__ = [
    "ConsoleEmailService",
    "EmailMessage",
    "EmailService",
    "SMTPEmailService",
    "build_email_service",
]
