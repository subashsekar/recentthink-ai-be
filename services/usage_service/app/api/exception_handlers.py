"""Global exception handlers for the Usage Service API."""

from __future__ import annotations

from fastapi import FastAPI

from shared.api.exception_handlers import register_core_exception_handlers


def register_exception_handlers(app: FastAPI) -> None:
    """Attach consistent HTTP handlers for domain and validation errors."""
    register_core_exception_handlers(
        app,
        validation_status_code=422,
    )
