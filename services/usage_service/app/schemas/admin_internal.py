"""Schemas for Usage Service internal admin APIs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FeatureUsageItem(BaseModel):
    feature: str
    requests: int


class UsageAnalyticsResponse(BaseModel):
    total_requests: int = 0
    daily_requests: int = 0
    monthly_requests: int = 0
    token_usage: int = 0
    top_features: list[FeatureUsageItem] = Field(default_factory=list)


class UserUsageResponse(BaseModel):
    items: list[dict] = Field(default_factory=list)
