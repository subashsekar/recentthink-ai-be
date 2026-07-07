"""Cost calculator tests."""

from __future__ import annotations

from app.core.config import AIServiceSettings
from app.utils.cost_calculator import CostCalculator, CostEstimate


def test_estimate_request_cost() -> None:
    settings = AIServiceSettings(
        model_cost_per_1k_input_tokens=0.001,
        model_cost_per_1k_output_tokens=0.002,
        usd_to_inr_rate=80.0,
    )
    calc = CostCalculator(settings=settings, usd_to_inr_rate=80.0)
    result = calc.estimate_request_cost(input_tokens=1000, output_tokens=500)
    assert result.usd == 0.002
    assert result.inr == 0.16
    assert result.total_tokens == 1500


def test_aggregate_daily() -> None:
    records = [
        CostEstimate(usd=0.01, inr=0.83, input_tokens=100, output_tokens=50, total_tokens=150),
        CostEstimate(usd=0.02, inr=1.66, input_tokens=200, output_tokens=100, total_tokens=300),
    ]
    summary = CostCalculator.aggregate_daily(records)
    assert summary.request_count == 2
    assert summary.total_usd == 0.03
    assert summary.total_tokens == 450


def test_aggregate_monthly() -> None:
    records = [
        CostEstimate(usd=0.01, inr=0.83, input_tokens=10, output_tokens=10, total_tokens=20),
    ]
    summary = CostCalculator.aggregate_monthly(records)
    assert summary.request_count == 1
