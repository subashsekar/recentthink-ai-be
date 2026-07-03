"""Provider-agnostic email delivery interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EmailMessage:
    """An outbound email ready to be dispatched by a transport.

    Presentation concerns (subject, HTML/text bodies) are resolved by the
    caller (see :mod:`app.services.email.templates`) so transports stay
    focused solely on delivery.
    """

    to_email: str
    subject: str
    html_body: str
    text_body: str | None = None


class EmailService(ABC):
    """Abstraction over a transactional email transport.

    Concrete implementations (SMTP, console, future third-party providers)
    implement :meth:`send_email`. Callers depend on this interface only, which
    keeps business logic decoupled from any specific provider (Dependency
    Inversion Principle).
    """

    @abstractmethod
    def send_email(self, message: EmailMessage) -> None:
        """Dispatch ``message`` to its recipient.

        Raises:
            shared.exceptions.email.EmailDeliveryError: If the transport could
                not deliver the message.
        """
        raise NotImplementedError
