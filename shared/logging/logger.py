"""Shared logging helpers."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from shared.config import Environment, get_settings


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


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger configured with the application log level."""
    root = logging.getLogger()
    if not root.handlers:
        settings = get_settings()
        handler = logging.StreamHandler()
        if settings.environment in {Environment.PRODUCTION, Environment.STAGING}:
            handler.setFormatter(StructuredFormatter())
        else:
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                ),
            )
        root.addHandler(handler)
        root.setLevel(settings.log_level.value)
    return logging.getLogger(name)
