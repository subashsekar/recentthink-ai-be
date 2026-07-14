"""Shared logging helpers."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from shared.config import Environment, LogLevel, get_settings


class StructuredFormatter(logging.Formatter):
    """Emit log records as single-line JSON for production observability."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1] is not None:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def _use_json_logs(settings: object) -> bool:
    """Prefer JSON when LOG_FORMAT=json or when running in staging/production."""
    explicit = os.getenv("LOG_FORMAT", "").strip().lower()
    if explicit in {"json", "structured"}:
        return True
    if explicit in {"text", "plain"}:
        return False
    environment = getattr(settings, "environment", None)
    return environment in {Environment.PRODUCTION, Environment.STAGING}


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger configured with the application log level."""
    root = logging.getLogger()
    if not root.handlers:
        settings = get_settings()
        handler = logging.StreamHandler()
        if _use_json_logs(settings):
            handler.setFormatter(StructuredFormatter())
        else:
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                ),
            )
        root.addHandler(handler)
        # No DEBUG noise in production containers.
        level = settings.log_level
        if settings.environment is Environment.PRODUCTION and level is LogLevel.DEBUG:
            level = LogLevel.INFO
        root.setLevel(level.value)
    return logging.getLogger(name)
