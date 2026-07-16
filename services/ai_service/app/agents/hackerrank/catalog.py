"""HackerRank catalog helpers (modes + examples)."""

from __future__ import annotations

from app.agents.hackerrank.schemas import HackerrankExampleResponse, HackerrankModeResponse
from app.coaching.registry import DEFAULT_MODE_ID, get_mode_registry
from shared.exceptions.base import ValidationException


def allowed_mode_ids() -> list[str]:
    return [m.id for m in get_mode_registry().list_metadata()]


def list_modes() -> list[HackerrankModeResponse]:
    """Return coaching modes for the HackerRank workspace header."""
    modes = get_mode_registry().list_metadata()
    return [
        HackerrankModeResponse(
            id=item.id,
            label=item.label,
            description=item.description or None,
            icon=item.icon or None,
            recommended=bool(item.recommended),
        )
        for item in modes
    ]


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


def validate_mode_id(mode_id: str) -> None:
    """Reject unknown coaching mode IDs."""
    if mode_id not in allowed_mode_ids():
        raise ValidationException(
            f"Unknown mode_id '{mode_id}'. Use GET /hackerrank/modes for valid ids.",
        )


def resolve_mode_id(
    *,
    requested: str | None = None,
    session_mode_id: str | None = None,
) -> str:
    """Pick mode: explicit request → session → default learning."""
    if requested is not None:
        validate_mode_id(requested)
        return requested
    if isinstance(session_mode_id, str) and session_mode_id:
        validate_mode_id(session_mode_id)
        return session_mode_id
    return DEFAULT_MODE_ID


__all__ = [
    "DEFAULT_MODE_ID",
    "allowed_mode_ids",
    "list_examples",
    "list_modes",
    "resolve_mode_id",
    "validate_mode_id",
]
