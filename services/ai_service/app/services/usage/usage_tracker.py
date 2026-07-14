"""Usage tracking integration."""

from __future__ import annotations

from uuid import UUID

from app.clients.usage import UsageServiceClient
from app.repositories.model_usage_repository import ModelUsageRepository
from shared.logging import get_logger

logger = get_logger(__name__)


class UsageTracker:
    """Centralized usage tracking — Usage Service + local model_usage."""

    def __init__(
        self,
        *,
        usage_client: UsageServiceClient | None = None,
        model_usage_repo: ModelUsageRepository | None = None,
    ) -> None:
        self._usage_client = usage_client or UsageServiceClient()
        self._model_usage_repo = model_usage_repo

    async def record_request(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        feature: str,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        execution_time_ms: int,
        estimated_cost: float,
        request_count: int = 1,
        section_tokens: dict[str, int] | None = None,
    ) -> None:
        total_tokens = input_tokens + output_tokens
        if self._model_usage_repo is not None:
            self._model_usage_repo.create_usage(
                session_id=session_id,
                user_id=user_id,
                model=model,
                provider=provider,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                estimated_cost=estimated_cost,
            )

        await self._usage_client.record_usage(
            user_id=user_id,
            feature=feature,
            token_usage=total_tokens,
            execution_time_ms=execution_time_ms,
            session_id=session_id,
            request_count=request_count,
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            model=model,
            provider=provider,
            estimated_cost=estimated_cost,
            success=True,
            section_tokens=section_tokens,
        )

        logger.info(
            "usage_recorded",
            extra={
                "user_id": str(user_id),
                "session_id": str(session_id),
                "feature": feature,
                "model": model,
                "provider": provider,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "latency_ms": latency_ms,
                "execution_time_ms": execution_time_ms,
                "estimated_cost": estimated_cost,
                "section_tokens": section_tokens,
            },
        )
