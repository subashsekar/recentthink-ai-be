"""Feature-specific OpenRouter max_tokens limits.

One global token limit is never used — each AI product selects its own cap.
"""

from __future__ import annotations

from typing import Final

# Sprint-defined feature limits (completion budget for ONE OpenRouter call).
# DSA Pattern + Course need large nested JSON — low caps truncate and yield empty/sparse output.
FEATURE_MAX_TOKENS: Final[dict[str, int]] = {
    "leetcode": 1800,
    "hackerrank": 1800,
    "dsa": 8192,
    "dsa_pattern": 8192,
    "course_generator": 12288,
    "course": 12288,
    "interview": 2200,
}

_DEFAULT_MAX_TOKENS: Final[int] = 1800

# Top-level workflow modules that can be requested independently.
TOP_LEVEL_SECTIONS: Final[frozenset[str]] = frozenset(
    {"teacher", "coder", "evaluator", "code_explainer"},
)

# Nested feature payload keys that support incremental regeneration.
NESTED_SECTIONS: Final[frozenset[str]] = frozenset(
    {
        "practice",
        "recognition",
        "visualization",
        "quiz",
        "assignment",
        "assignments",
        "project",
        "projects",
        "assessment",
        "assessments",
        "overview",
        "mental_model",
        "templates",
        "roadmap",
        "lessons",
        "resources",
        "tips",
    },
)


def resolve_feature_max_tokens(
    feature: str,
    *,
    override: int | None = None,
    requested_sections: list[str] | None = None,
    limits: dict[str, int] | None = None,
) -> int:
    """Return max_tokens for ``feature``.

    Explicit ``override`` (from the client) wins when provided and positive.
    When only a subset of sections is requested, scale the budget down so
    unused sections do not inflate cost.
    """
    table = limits or FEATURE_MAX_TOKENS
    if override is not None and override > 0:
        base = int(override)
    else:
        base = table.get(feature.strip().lower(), _DEFAULT_MAX_TOKENS)

    if not requested_sections:
        return base

    scale = min(1.0, max(0.25, len(requested_sections) / 6.0))
    return max(400, min(base, int(base * scale)))
