"""HackerRank catalog helpers (examples)."""

from __future__ import annotations

from app.agents.hackerrank.schemas import HackerrankExampleResponse


def list_examples() -> list[HackerrankExampleResponse]:
    # Keep small + stable; frontend hero cards.
    return [
        HackerrankExampleResponse(
            id="solve-me-first",
            title="Solve Me First",
            difficulty="Easy",
            domain="Algorithms",
            url="https://www.hackerrank.com/challenges/solve-me-first/problem",
            icon="bolt",
        ),
        HackerrankExampleResponse(
            id="two-strings",
            title="Two Strings",
            difficulty="Easy",
            domain="Algorithms",
            url="https://www.hackerrank.com/challenges/two-strings/problem",
            icon="code",
        ),
        HackerrankExampleResponse(
            id="weather-observation-station-1",
            title="Weather Observation Station 1",
            difficulty="Easy",
            domain="SQL",
            url="https://www.hackerrank.com/challenges/weather-observation-station-1/problem",
            icon="database",
        ),
    ]


__all__ = ["list_examples"]

