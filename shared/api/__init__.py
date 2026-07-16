"""Shared API-layer helpers (exception responses, pagination, etc.)."""

from shared.api.exception_handlers import (
    INTERNAL_ERROR_DETAIL,
    RATE_LIMIT_DETAIL,
    error_response,
    register_core_exception_handlers,
    register_rate_limit_handler,
    request_context,
    validation_error_detail,
)

__all__ = [
    "INTERNAL_ERROR_DETAIL",
    "RATE_LIMIT_DETAIL",
    "error_response",
    "register_core_exception_handlers",
    "register_rate_limit_handler",
    "request_context",
    "validation_error_detail",
]
