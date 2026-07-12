"""Analytics aggregation from AI + Usage services."""

from __future__ import annotations

import asyncio

from app.clients.ai_client import AIServiceClient
from app.clients.usage_client import UsageServiceClient
from app.schemas.admin import (
    AnalyticsResponse,
    ModelAnalyticsResponse,
    UsageAnalyticsResponse,
)


class AnalyticsService:
    def __init__(
        self,
        *,
        ai_client: AIServiceClient,
        usage_client: UsageServiceClient,
    ) -> None:
        self._ai = ai_client
        self._usage = usage_client

    async def get_ai_analytics(self) -> AnalyticsResponse:
        data = await self._ai.analytics()
        return AnalyticsResponse(**data)

    async def get_usage_analytics(self) -> UsageAnalyticsResponse:
        usage, models = await asyncio.gather(
            self._usage.analytics(),
            self._ai.models(),
        )
        provider_usage = models.get("provider_usage", [])
        model_usage = models.get("model_usage", [])
        estimated_cost = sum(float(item.get("estimated_cost", 0)) for item in model_usage)
        return UsageAnalyticsResponse(
            total_requests=int(usage.get("total_requests", 0)),
            daily_requests=int(usage.get("daily_requests", 0)),
            monthly_requests=int(usage.get("monthly_requests", 0)),
            token_usage=int(usage.get("token_usage", 0)),
            top_features=list(usage.get("top_features", [])),
            provider_usage=list(provider_usage),
            model_usage=list(model_usage),
            estimated_cost=estimated_cost,
        )

    async def get_model_analytics(self) -> ModelAnalyticsResponse:
        data = await self._ai.models()
        return ModelAnalyticsResponse(**data)
