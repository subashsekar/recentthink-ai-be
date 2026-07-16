"""Shared API-layer helpers (exception responses, pagination, etc.)."""

from shared.api.exception_handlers import INTERNAL_ERROR_DETAIL, error_response, request_context

__all__ = [
    "INTERNAL_ERROR_DETAIL",
    "error_response",
    "request_context",
]
