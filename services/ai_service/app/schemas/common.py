"""Shared API schemas used across agent routers."""

from __future__ import annotations

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Consistent API error payload."""

    detail: str
