"""Chat assistant message metadata helpers."""

from __future__ import annotations

from typing import Any

from app.core.config import get_ai_settings
from app.core.feature_tokens import TOP_LEVEL_SECTIONS
from app.schemas.ai import ChatResponse

_FINISH_REASON_TRUNCATED = frozenset({"length", "max_tokens", "truncated"})


def is_truncated_finish_reason(finish_reason: str | None) -> bool:
    if not finish_reason:
        return False
    return finish_reason.strip().lower() in _FINISH_REASON_TRUNCATED


def section_has_content(payload: dict[str, Any], section: str) -> bool:
    key = section.strip().lower()
    value = payload.get(key)
    if value is None and key in ("course", "dsa_pattern", "interview", "feature"):
        value = payload.get(key)
    if value is None:
        for nest_key in ("course", "dsa_pattern", "interview", "feature"):
            nest = payload.get(nest_key)
            if isinstance(nest, dict) and key in nest and nest[key] is not None:
                value = nest[key]
                break
    if value is None:
        return False
    if isinstance(value, dict):
        return bool(value)
    if isinstance(value, str):
        return bool(value.strip())
    return True


def compute_missing_sections(
    *,
    expected_sections: list[str] | None,
    llm_raw: dict[str, Any] | None,
) -> list[str] | None:
    """Return top-level sections that were expected but missing or empty in the payload."""
    if not expected_sections:
        return None
    payload = llm_raw or {}
    missing = [section for section in expected_sections if not section_has_content(payload, section)]
    return missing or None


def resolve_message_status(
    *,
    finish_reason: str | None,
    missing_sections: list[str] | None,
    errors: list[str] | None = None,
) -> str:
    if errors:
        return "failed"
    if is_truncated_finish_reason(finish_reason) or missing_sections:
        return "truncated"
    return "completed"


def build_assistant_metadata(
    response: ChatResponse,
    *,
    action: str,
    status: str,
    finish_reason: str | None = None,
    missing_sections: list[str] | None = None,
    requested_sections: list[str] | None = None,
    cache_hit: bool = False,
    retry_count: int = 0,
    generation_type: str | None = None,
    prior_message_id: str | None = None,
    regenerated_from_message_id: str | None = None,
    structured: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build persisted assistant ``content_metadata`` for chat actions."""
    from app.models.enums import ModuleName

    metadata: dict[str, Any] = {
        "status": status,
        "action": action,
        "prompt_version": get_ai_settings().prompt_default_version,
        "model": response.model,
        "provider": response.provider,
        "prompt_tokens": response.input_tokens,
        "completion_tokens": response.output_tokens,
        "total_tokens": response.total_tokens,
        "execution_time_ms": response.execution_time_ms,
        "finish_reason": finish_reason,
        "missing_sections": missing_sections,
        "requested_sections": list(requested_sections) if requested_sections else None,
        "section_tokens": response.section_tokens,
        "cache_hit": cache_hit,
        "retry_count": retry_count,
        "generation_type": generation_type or action,
    }
    if prior_message_id:
        metadata["supersedes_message_id"] = prior_message_id
    if regenerated_from_message_id:
        metadata["regenerated_from_message_id"] = regenerated_from_message_id
    if structured:
        metadata["structured"] = structured
    elif response.modules:
        teacher = next((module for module in response.modules if module.module == ModuleName.TEACHER), None)
        if teacher and teacher.structured:
            metadata["structured"] = teacher.structured
            metadata["markdown"] = teacher.content
    return metadata


def expected_sections_from_planner(planner_modules: list[str] | None) -> list[str] | None:
    if not planner_modules:
        return None
    top = [module for module in planner_modules if module in TOP_LEVEL_SECTIONS]
    return top or None


def should_hide_message(metadata: dict[str, Any] | None, *, include_hidden: bool) -> bool:
    if include_hidden or not metadata:
        return False
    if metadata.get("deleted"):
        return True
    status = str(metadata.get("status", "")).lower()
    if status in {"superseded", "failed"}:
        return True
    return False
