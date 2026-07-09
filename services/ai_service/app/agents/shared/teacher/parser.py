"""Parse teacher JSON from LLM follow-up / chat responses."""

from __future__ import annotations

import json
from typing import Any

from app.agents.shared.base import extract_json_object
from app.agents.shared.llm_response_normalizer import normalize_unified_llm_payload


def _teacher_has_content(teacher: dict[str, Any]) -> bool:
    text_fields = (
        "problem_summary",
        "thinking_process",
        "approach",
        "analogy",
        "next_step",
        "explanation",
    )
    if any(str(teacher.get(key, "")).strip() for key in text_fields):
        return True
    return bool(
        teacher.get("concepts")
        or teacher.get("hints")
        or teacher.get("learning_objectives")
        or teacher.get("common_mistakes"),
    )


def parse_teacher_payload(
    content: str,
    *,
    planner_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Parse and normalize teacher JSON from an LLM response."""
    text = content.strip()
    if not text:
        return normalize_unified_llm_payload(
            {"teacher": {}, "coder": {}, "evaluator": {}},
            planner_metadata=planner_metadata,
        )["teacher"]

    try:
        parsed = extract_json_object(text)
        if isinstance(parsed, dict) and isinstance(parsed.get("teacher"), dict):
            parsed = parsed["teacher"]
        if isinstance(parsed, dict):
            normalized = normalize_unified_llm_payload(
                {"teacher": parsed, "coder": {}, "evaluator": {}},
                planner_metadata=planner_metadata,
            )["teacher"]
            if _teacher_has_content(normalized):
                return normalized
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    fallback_text = text
    if fallback_text.startswith("{"):
        fallback_text = (
            "Here is a direct answer to your follow-up question:\n\n"
            + fallback_text
        )
    return normalize_unified_llm_payload(
        {"teacher": {"explanation": fallback_text}, "coder": {}, "evaluator": {}},
        planner_metadata=planner_metadata,
    )["teacher"]
