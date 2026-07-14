"""Usage metering use-case service."""

from __future__ import annotations

from app.repositories.usage_record_repository import UsageRecordRepository
from app.schemas.usage import RecordUsageRequest, RecordUsageResponse


class UsageService:
    """Handles usage metering operations."""

    def __init__(self, repository: UsageRecordRepository) -> None:
        self._repo = repository

    def record_usage(self, request: RecordUsageRequest) -> RecordUsageResponse:
        prompt = request.prompt_tokens
        completion = request.completion_tokens
        total = request.token_usage or (prompt + completion)
        record = self._repo.create_record(
            user_id=request.user_id,
            service_name=request.service_name,
            feature=request.feature,
            request_count=request.request_count,
            token_usage=total,
            prompt_tokens=prompt,
            completion_tokens=completion,
            execution_time_ms=request.execution_time_ms,
            session_id=request.session_id,
            model=request.model,
            provider=request.provider,
            estimated_cost=request.estimated_cost,
            success=request.success,
            section_tokens=request.section_tokens,
        )
        return RecordUsageResponse(id=record.id)
