"""Usage metering use-case service."""

from __future__ import annotations

from app.repositories.usage_record_repository import UsageRecordRepository
from app.schemas.usage import RecordUsageRequest, RecordUsageResponse


class UsageService:
    """Handles usage metering operations."""

    def __init__(self, repository: UsageRecordRepository) -> None:
        self._repo = repository

    def record_usage(self, request: RecordUsageRequest) -> RecordUsageResponse:
        record = self._repo.create_record(
            user_id=request.user_id,
            service_name=request.service_name,
            feature=request.feature,
            request_count=request.request_count,
            token_usage=request.token_usage,
            execution_time_ms=request.execution_time_ms,
            session_id=request.session_id,
        )
        return RecordUsageResponse(id=record.id)
