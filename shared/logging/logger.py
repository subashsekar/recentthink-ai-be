"""Shared logging helpers."""

from __future__ import annotations

import logging

from shared.config import get_settings


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger configured with the application log level."""
    logger = logging.getLogger(name)
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=get_settings().log_level.value,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
    return logger
