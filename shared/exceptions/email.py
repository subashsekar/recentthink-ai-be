"""Email delivery exceptions."""

from __future__ import annotations


class EmailError(Exception):
    """Base class for email subsystem errors."""


class EmailDeliveryError(EmailError):
    """Raised when an email could not be dispatched by the transport.

    Represents an infrastructure failure (SMTP unavailable, provider rejected
    the message, etc.) rather than a client mistake, so it maps to a 5xx
    response at the API boundary.
    """
