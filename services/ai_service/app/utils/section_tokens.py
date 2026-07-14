"""Estimate completion tokens attributed to each logical response section.

OpenRouter returns a single completion_tokens total for the unified JSON
response. We apportion that total by serialized section size so Admin/Usage
analytics can report cost drivers without a second LLM call.
"""

from __future__ import annotations

import json
from typing import Any


def estimate_section_tokens(
    payload: dict[str, Any] | None,
    *,
    completion_tokens: int,
    requested_sections: list[str] | None = None,
) -> dict[str, int]:
    """Distribute ``completion_tokens`` across top-level + nested sections."""
    if not payload or completion_tokens <= 0:
        return {}

    weights: dict[str, int] = {}

    for key in ("teacher", "coder", "evaluator", "code_explainer"):
        value = payload.get(key)
        if value is not None:
            weights[key] = _size(value)

    # Nested product payloads live under ``feature`` or legacy aliases.
    for nest_key in ("feature", "course", "dsa_pattern", "interview"):
        nest = payload.get(nest_key)
        if isinstance(nest, dict):
            for child_key, child_val in nest.items():
                if child_val is None:
                    continue
                weights[str(child_key)] = _size(child_val)

    if requested_sections:
        allowed = {s.strip().lower() for s in requested_sections}
        weights = {k: v for k, v in weights.items() if k.lower() in allowed}

    total_weight = sum(weights.values())
    if total_weight <= 0:
        return {}

    # Largest-remainder so integers sum to completion_tokens.
    raw = {
        key: (completion_tokens * weight) / total_weight
        for key, weight in weights.items()
    }
    floors = {key: int(value) for key, value in raw.items()}
    remainder = completion_tokens - sum(floors.values())
    by_frac = sorted(
        raw.keys(),
        key=lambda k: (raw[k] - floors[k], weights[k]),
        reverse=True,
    )
    for key in by_frac:
        if remainder <= 0:
            break
        floors[key] += 1
        remainder -= 1
    return {key: value for key, value in floors.items() if value > 0}


def _size(value: Any) -> int:
    try:
        return max(1, len(json.dumps(value, default=str)))
    except (TypeError, ValueError):
        return max(1, len(str(value)))


def merge_llm_payload(
    prior: dict[str, Any] | None,
    generated: dict[str, Any],
    *,
    requested_sections: list[str] | None,
) -> dict[str, Any]:
    """Merge newly generated sections into a prior unified payload.

    Unchanged sections from ``prior`` are reused. When ``requested_sections``
    is empty/None, ``generated`` replaces the whole payload.
    """
    if not requested_sections:
        return generated

    allowed = {s.strip().lower() for s in requested_sections}
    merged: dict[str, Any] = dict(prior or {})

    for key in ("teacher", "coder", "evaluator", "code_explainer"):
        if key in allowed and key in generated:
            merged[key] = generated[key]

    for nest_key in ("feature", "course", "dsa_pattern", "interview"):
        gen_nest = generated.get(nest_key)
        if not isinstance(gen_nest, dict):
            continue
        base_nest = dict(merged.get(nest_key) or {}) if isinstance(merged.get(nest_key), dict) else {}
        for child_key, child_val in gen_nest.items():
            if child_key.lower() in allowed or nest_key in allowed:
                base_nest[child_key] = child_val
        # Also accept abbreviated plural→singular aliases.
        for section in allowed:
            if section in gen_nest:
                base_nest[section] = gen_nest[section]
        if base_nest:
            merged[nest_key] = base_nest
            if nest_key != "feature" and "feature" not in merged:
                merged["feature"] = base_nest

    # Preserve metadata when present.
    if "metadata" in generated:
        merged["metadata"] = generated["metadata"]
    return merged


def filter_payload_to_sections(
    payload: dict[str, Any] | None,
    requested_sections: list[str] | None,
) -> dict[str, Any]:
    """Return a copy of ``payload`` containing only requested sections."""
    if not payload:
        return {}
    if not requested_sections:
        return dict(payload)

    allowed = {s.strip().lower() for s in requested_sections}
    filtered: dict[str, Any] = {}

    for key in ("teacher", "coder", "evaluator", "code_explainer"):
        if key in allowed and key in payload:
            filtered[key] = payload[key]

    for nest_key in ("feature", "course", "dsa_pattern", "interview"):
        nest = payload.get(nest_key)
        if not isinstance(nest, dict):
            continue
        child: dict[str, Any] = {}
        for child_key, child_val in nest.items():
            if child_key.lower() in allowed or nest_key in allowed:
                child[child_key] = child_val
        if child:
            filtered[nest_key] = child

    if "metadata" in payload:
        filtered["metadata"] = payload["metadata"]
    return filtered


def resolve_prior_payload(
    *,
    context: dict[str, Any] | None,
    memory_context: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Locate a prior unified LLM payload for incremental merge."""
    ctx = context or {}
    for key in ("prior_llm_raw", "existing_response", "existing_sections"):
        value = ctx.get(key)
        if isinstance(value, dict) and value:
            return value

    mem = memory_context or {}
    prior: dict[str, Any] = {}
    if isinstance(mem.get("teacher_output"), dict):
        prior["teacher"] = mem["teacher_output"]
    if isinstance(mem.get("coder_output"), dict):
        prior["coder"] = mem["coder_output"]
    if isinstance(mem.get("evaluator_output"), dict):
        prior["evaluator"] = mem["evaluator_output"]
    feature = mem.get("feature_payload") or mem.get("dsa_pattern") or mem.get("course")
    if isinstance(feature, dict) and feature:
        prior["feature"] = feature
    return prior or None
