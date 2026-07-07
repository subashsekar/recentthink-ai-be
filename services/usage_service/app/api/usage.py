"""Usage metering HTTP routes."""

from __future__ import annotations

from app.dependencies.auth import require_internal_service
from app.dependencies.services import get_usage_service
from app.schemas.usage import RecordUsageRequest, RecordUsageResponse
from app.services.usage_service import UsageService
from fastapi import APIRouter, Depends, status

router = APIRouter(prefix="/usage", tags=["usage"])


@router.post(
    "/record",
    response_model=RecordUsageResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_usage(
    payload: RecordUsageRequest,
    _service_auth: None = Depends(require_internal_service),
    usage_service: UsageService = Depends(get_usage_service),
) -> RecordUsageResponse:
    """Record a usage metering event from an authenticated internal service."""
    return usage_service.record_usage(payload)
