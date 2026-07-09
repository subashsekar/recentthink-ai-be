"""Normalize and enrich single-LLM JSON before processing modules."""

from __future__ import annotations

from typing import Any

_TEACHER_TEXT_KEYS = (
    "problem_summary",
    "thinking_process",
    "approach",
    "analogy",
    "next_step",
    "explanation",
)

_CODER_STRUCTURED_KEYS = ("brute_force", "better_solution", "optimal_solution")
_CODER_STRUCTURED_ALIASES = {
    "better": "better_solution",
    "optimal": "optimal_solution",
}
_SOLUTION_SLOT_KEYS = ("brute_force", "better_solution", "optimal_solution")


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _solution_has_code(solution: Any) -> bool:
    return isinstance(solution, dict) and bool(str(solution.get("code", "")).strip())


def _teacher_has_content(teacher: dict[str, Any]) -> bool:
    if any(str(teacher.get(key, "")).strip() for key in _TEACHER_TEXT_KEYS):
        return True
    if teacher.get("concepts") or teacher.get("hints") or teacher.get("learning_objectives"):
        return True
    return False


def _coder_has_content(coder: dict[str, Any]) -> bool:
    for key in _CODER_STRUCTURED_KEYS:
        if _solution_has_code(coder.get(key)):
            return True
    for alias in _CODER_STRUCTURED_ALIASES:
        if _solution_has_code(coder.get(alias)):
            return True
    for solution in coder.get("solutions") or []:
        if _solution_has_code(solution):
            return True
    return False


def is_llm_response_empty(payload: dict[str, Any]) -> bool:
    """Return True when teacher and coder sections lack usable content."""
    teacher = _as_dict(payload.get("teacher"))
    coder = _as_dict(payload.get("coder"))
    return not _teacher_has_content(teacher) and not _coder_has_content(coder)


def _normalize_solution(
    raw: dict[str, Any],
    *,
    default_language: str,
    default_approach: str,
) -> dict[str, Any]:
    return {
        "language": str(raw.get("language") or default_language or "python"),
        "code": str(raw.get("code") or ""),
        "explanation": str(raw.get("explanation") or raw.get("approach") or default_approach),
        "complexity": str(raw.get("complexity") or ""),
        "approach": str(raw.get("approach") or default_approach),
    }


def _normalize_teacher(
    teacher: dict[str, Any],
    planner_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = dict(teacher)
    explanation = str(normalized.get("explanation", "")).strip()
    if not str(normalized.get("problem_summary", "")).strip() and explanation:
        normalized["problem_summary"] = explanation
    if not str(normalized.get("thinking_process", "")).strip():
        approach = str(normalized.get("approach", "")).strip()
        if approach:
            normalized["thinking_process"] = approach

    metadata = planner_metadata or {}
    if not normalized.get("learning_objectives"):
        objectives = metadata.get("learning_objectives")
        if objectives:
            normalized["learning_objectives"] = list(objectives)
    if not normalized.get("concepts"):
        patterns = metadata.get("patterns")
        if patterns:
            normalized["concepts"] = list(patterns)
    if not normalized.get("common_mistakes"):
        mistakes = metadata.get("common_mistakes")
        if mistakes:
            normalized["common_mistakes"] = list(mistakes)
    return normalized


def _normalize_coder(coder: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(coder)
    for alias, canonical in _CODER_STRUCTURED_ALIASES.items():
        if alias in normalized and canonical not in normalized:
            normalized[canonical] = normalized.pop(alias)

    default_language = str(normalized.get("language") or "python")
    for key in _CODER_STRUCTURED_KEYS:
        raw = normalized.get(key)
        if isinstance(raw, dict):
            normalized[key] = _normalize_solution(
                raw,
                default_language=default_language,
                default_approach=key.replace("_", " ").title(),
            )

    solutions = normalized.get("solutions") or []
    has_structured = any(_solution_has_code(normalized.get(key)) for key in _CODER_STRUCTURED_KEYS)
    if isinstance(solutions, list) and solutions and not has_structured:
        labels = ("Brute Force", "Better Solution", "Optimal Solution")
        for index, raw_solution in enumerate(solutions[:3]):
            if not isinstance(raw_solution, dict) or not _solution_has_code(raw_solution):
                continue
            slot = _SOLUTION_SLOT_KEYS[index]
            normalized[slot] = _normalize_solution(
                raw_solution,
                default_language=default_language,
                default_approach=str(raw_solution.get("approach") or labels[index]),
            )
    return normalized


def _normalize_evaluator(evaluator: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(evaluator)
    if not normalized.get("follow_up_questions") and normalized.get("interview_questions"):
        normalized["follow_up_questions"] = list(normalized["interview_questions"])
    if not normalized.get("mistakes") and normalized.get("common_mistakes"):
        normalized["mistakes"] = list(normalized["common_mistakes"])
    return normalized


def normalize_unified_llm_payload(
    payload: dict[str, Any],
    *,
    planner_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Map common LLM key variants to the schema expected by processing modules."""
    return {
        "teacher": _normalize_teacher(_as_dict(payload.get("teacher")), planner_metadata),
        "coder": _normalize_coder(_as_dict(payload.get("coder"))),
        "evaluator": _normalize_evaluator(_as_dict(payload.get("evaluator"))),
    }
