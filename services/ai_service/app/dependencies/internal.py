"""Internal service-to-service authentication for AI Service."""

from __future__ import annotations

from typing import Annotated

from fastapi import Header

from shared.config import get_settings
from shared.security.service_auth import (
    INTERNAL_SERVICE_TOKEN_HEADER,
    verify_internal_service_token,
)


def require_internal_service(
    x_internal_service_token: Annotated[
        str | None,
        Header(alias=INTERNAL_SERVICE_TOKEN_HEADER),
    ] = None,
) -> None:
    verify_internal_service_token(x_internal_service_token, settings=get_settings())
