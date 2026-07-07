"""Reusable cost calculator for LLM usage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.config import AIServiceSettings, get_ai_settings


@dataclass(frozen=True)
class CostEstimate:
    """Estimated cost for a single request."""

    usd: float
    inr: float
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class CostSummary:
    """Aggregated cost over a time window."""

    total_usd: float
    total_inr: float
    request_count: int
    total_tokens: int


class CostCalculator:
    """Calculate estimated USD and INR costs from token usage."""

    DEFAULT_USD_TO_INR: float = 83.0

    def __init__(
        self,
        *,
        settings: AIServiceSettings | None = None,
        usd_to_inr_rate: float | None = None,
    ) -> None:
        self._settings = settings or get_ai_settings()
        self._usd_to_inr = usd_to_inr_rate or self.DEFAULT_USD_TO_INR

    def estimate_request_cost(
        self,
        *,
        input_tokens: int,
        output_tokens: int,
    ) -> CostEstimate:
        input_cost = (input_tokens / 1000) * self._settings.model_cost_per_1k_input_tokens
        output_cost = (output_tokens / 1000) * self._settings.model_cost_per_1k_output_tokens
        usd = round(input_cost + output_cost, 8)
        inr = round(usd * self._usd_to_inr, 4)
        total = input_tokens + output_tokens
        return CostEstimate(
            usd=usd,
            inr=inr,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total,
        )

    @staticmethod
    def aggregate_daily(
        records: list[CostEstimate],
        *,
        day: datetime | None = None,
    ) -> CostSummary:
        """Aggregate cost records for a single day (filtering is caller's responsibility)."""
        _ = day or datetime.now(UTC)
        total_usd = sum(record.usd for record in records)
        total_inr = sum(record.inr for record in records)
        total_tokens = sum(record.total_tokens for record in records)
        return CostSummary(
            total_usd=round(total_usd, 8),
            total_inr=round(total_inr, 4),
            request_count=len(records),
            total_tokens=total_tokens,
        )

    @staticmethod
    def aggregate_monthly(records: list[CostEstimate]) -> CostSummary:
        """Aggregate cost records for a month."""
        return CostCalculator.aggregate_daily(records)
