"""Placeholder domain events for cross-service account lifecycle hooks."""

from __future__ import annotations

from uuid import UUID

from shared.logging import get_logger
from shared.logging.security import log_security_event

logger = get_logger(__name__)


def publish_account_deleted(user_id: UUID, *, email: str | None = None) -> None:
    """Emit an AccountDeleted event for downstream services (placeholder).

    AI / usage rows are not FK-linked to ``users``. Downstream consumers should
    subscribe here later to purge orphaned ``user_id`` data. For now this only
    logs a structured security event.
    """
    logger.info("AccountDeleted event (placeholder) user_id=%s", user_id)
    context: dict[str, str] = {"user_id": str(user_id)}
    if email:
        context["email"] = email
    log_security_event("account_deleted_event", **context)
