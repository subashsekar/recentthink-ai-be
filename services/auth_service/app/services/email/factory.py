"""Factory that selects an email transport from configuration."""

from __future__ import annotations

from app.services.email.base import EmailService
from app.services.email.console_sender import ConsoleEmailService
from app.services.email.smtp_sender import SMTPEmailService

from shared.config import EmailProvider, Settings, get_settings


def build_email_service(settings: Settings | None = None) -> EmailService:
    """Return the :class:`EmailService` implementation for the configured provider.

    Adding a new provider means adding a branch here (and its implementation);
    no calling code changes because everything depends on the abstraction.
    """
    cfg = settings or get_settings()

    if cfg.email_provider is EmailProvider.SMTP:
        if not cfg.smtp_host:  # pragma: no cover - guarded by settings validator
            raise ValueError("SMTP_HOST must be configured for the SMTP provider.")
        return SMTPEmailService(
            host=cfg.smtp_host,
            port=cfg.smtp_port,
            from_address=cfg.email_from_address,
            from_name=cfg.email_from_name,
            username=cfg.smtp_username,
            password=cfg.smtp_password,
            use_tls=cfg.smtp_use_tls,
            timeout_seconds=cfg.smtp_timeout_seconds,
        )

    return ConsoleEmailService(
        from_address=cfg.email_from_address,
        from_name=cfg.email_from_name,
    )
