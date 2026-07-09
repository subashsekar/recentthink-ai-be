"""Tests for LLM response normalization."""

from __future__ import annotations

from app.agents.shared.llm_response_normalizer import (
    is_llm_response_empty,
    normalize_unified_llm_payload,
)


def test_normalize_maps_explanation_to_problem_summary() -> None:
    payload = normalize_unified_llm_payload(
        {"teacher": {"explanation": "Use a hash map."}, "coder": {}, "evaluator": {}},
    )
    assert payload["teacher"]["problem_summary"] == "Use a hash map."


def test_normalize_maps_solutions_array_to_structured_coder() -> None:
    payload = normalize_unified_llm_payload(
        {
            "teacher": {"problem_summary": "Two Sum"},
            "coder": {
                "language": "python",
                "solutions": [
                    {"approach": "Brute Force", "code": "def bf(): pass", "complexity": "O(n^2)"},
                    {"approach": "Optimal", "code": "def opt(): pass", "complexity": "O(n)"},
                ],
            },
            "evaluator": {},
        },
    )
    assert payload["coder"]["brute_force"]["code"] == "def bf(): pass"
    assert payload["coder"]["better_solution"]["code"] == "def opt(): pass"


def test_normalize_maps_better_alias() -> None:
    payload = normalize_unified_llm_payload(
        {
            "teacher": {"approach": "Hash map"},
            "coder": {"better": {"code": "def x(): pass"}},
            "evaluator": {},
        },
    )
    assert payload["coder"]["better_solution"]["code"] == "def x(): pass"
    assert payload["teacher"]["thinking_process"] == "Hash map"


def test_is_llm_response_empty_detects_blank_payload() -> None:
    assert is_llm_response_empty({"teacher": {}, "coder": {}, "evaluator": {}}) is True
    assert is_llm_response_empty(
        {"teacher": {"hints": ["try hashing"]}, "coder": {}, "evaluator": {}},
    ) is False


def test_normalize_enriches_teacher_from_planner_metadata() -> None:
    payload = normalize_unified_llm_payload(
        {"teacher": {}, "coder": {}, "evaluator": {}},
        planner_metadata={
            "patterns": ["Array"],
            "learning_objectives": ["Recognize two pointers"],
        },
    )
    assert payload["teacher"]["concepts"] == ["Array"]
    assert payload["teacher"]["learning_objectives"] == ["Recognize two pointers"]
