"""Processing module unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

from app.agents.shared.coder.module import CoderModule
from app.agents.shared.evaluator.module import EvaluatorModule
from app.agents.shared.teacher.module import TeacherModule
from app.models.enums import ModuleName


def test_teacher_module_formats_markdown() -> None:
    module = TeacherModule()
    result = module.process(
        session_id=uuid4(),
        payload={
            "explanation": "Use a hash map.",
            "concepts": ["Hash Map"],
            "hints": ["Think about complements"],
        },
    )
    assert result.module == ModuleName.TEACHER
    assert "hash map" in result.content.lower()
    assert "Hash Map" in result.content


def test_coder_module_formats_code() -> None:
    module = CoderModule()
    result = module.process(
        session_id=uuid4(),
        payload={
            "language": "python",
            "solutions": [
                {
                    "approach": "Brute Force",
                    "code": "def solve(): pass",
                    "complexity": "O(n^2)",
                },
            ],
        },
    )
    assert result.module == ModuleName.CODER
    assert "```python" in result.content
    assert "Brute Force" in result.content


def test_evaluator_module_formats_feedback() -> None:
    module = EvaluatorModule()
    result = module.process(
        session_id=uuid4(),
        payload={
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "feedback": "Good approach.",
            "optimizations": ["Use two pointers"],
            "interview_questions": ["What if input is sorted?"],
            "analytics": {"confidence": 0.9},
        },
    )
    assert result.module == ModuleName.EVALUATOR
    assert "O(n)" in result.content
    assert result.metadata is not None


def test_coder_module_formats_structured_solutions() -> None:
    module = CoderModule()
    result = module.process(
        session_id=uuid4(),
        payload={
            "brute_force": {
                "language": "java",
                "code": "class Solution {}",
                "complexity": "O(n^2)",
            },
            "optimal_solution": {
                "language": "java",
                "code": "class Opt {}",
                "complexity": "O(n)",
            },
        },
    )
    assert "```java" in result.content
    assert "Brute Force" in result.content
    assert "Optimal Solution" in result.content


def test_evaluator_module_formats_mistakes_and_edge_cases() -> None:
    module = EvaluatorModule()
    result = module.process(
        session_id=uuid4(),
        payload={
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "mistakes": ["infinite loop"],
            "edge_cases": ["single element"],
            "follow_up_questions": ["Can you do O(1) space?"],
        },
    )
    assert "Common Mistakes" in result.content
    assert "Edge Cases" in result.content


def test_teacher_module_formats_all_sprint3_fields() -> None:
    module = TeacherModule()
    result = module.process(
        session_id=uuid4(),
        payload={
            "problem_summary": "Two Sum",
            "thinking_process": "Look for complements.",
            "concepts": ["Hash Map"],
            "approach": "Store seen values.",
            "common_mistakes": ["Nested loops"],
            "analogy": "Like finding matching socks.",
            "next_step": "Try an example.",
        },
    )
    assert result.module == ModuleName.TEACHER
    assert "Problem Summary" in result.content
    assert "Real World Analogy" in result.content
    assert "Recommended Next Step" in result.content
    assert result.metadata is not None
    assert len(result.metadata.get("cards", [])) >= 5


def test_teacher_module_formats_thinking_process() -> None:
    module = TeacherModule()
    result = module.process(
        session_id=uuid4(),
        payload={
            "thinking_process": "Break down the problem.",
            "approach": "Use sliding window.",
            "concepts": ["Two Pointers"],
        },
    )
    assert "Thinking Process" in result.content
    assert "sliding window" in result.content.lower()


def test_teacher_module_persists_message() -> None:
    repo = MagicMock()
    module = TeacherModule()
    session_id = uuid4()
    module.process(
        session_id=session_id,
        payload={"explanation": "Test"},
        message_repo=repo,
    )
    repo.create_message.assert_called_once()
