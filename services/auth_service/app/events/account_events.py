"""Cross-service account lifecycle hooks."""

from __future__ import annotations

from uuid import UUID

import httpx

from shared.config import get_settings
from shared.logging import get_logger
from shared.logging.security import log_security_event
from shared.security.service_auth import INTERNAL_SERVICE_TOKEN_HEADER

logger = get_logger(__name__)

_PURGE_TIMEOUT_SECONDS = 15.0


def publish_account_deleted(user_id: UUID, *, email: str | None = None) -> None:
    """Emit an AccountDeleted event and best-effort purge AI / Usage orphans.

    Auth account deletion must still succeed if downstream services are down —
    failures are logged as warnings and never raised.
    """
    logger.info("AccountDeleted event user_id=%s", user_id)
    context: dict[str, str] = {"user_id": str(user_id)}
    if email:
        context["email"] = email
    log_security_event("account_deleted_event", **context)

    settings = get_settings()
    headers = {INTERNAL_SERVICE_TOKEN_HEADER: settings.internal_service_token}
    targets = (
        ("ai_service", settings.ai_service_url),
        ("usage_service", settings.usage_service_url),
    )
    for name, base_url in targets:
        _best_effort_purge(name, base_url, user_id, headers=headers)


def _best_effort_purge(
    service_name: str,
    base_url: str,
    user_id: UUID,
    *,
    headers: dict[str, str],
) -> None:
    url = f"{base_url.rstrip('/')}/internal/admin/users/{user_id}"
    try:
        with httpx.Client(timeout=_PURGE_TIMEOUT_SECONDS) as client:
            response = client.delete(url, headers=headers)
        if response.status_code >= 400:
            logger.warning(
                "AccountDeleted purge failed service=%s status=%s body=%s",
                service_name,
                response.status_code,
                response.text[:500],
            )
        else:
            logger.info(
                "AccountDeleted purge ok service=%s user_id=%s",
                service_name,
                user_id,
            )
    except Exception as exc:
        logger.warning(
            "AccountDeleted purge unavailable service=%s user_id=%s error=%s",
            service_name,
            user_id,
            exc,
        )
