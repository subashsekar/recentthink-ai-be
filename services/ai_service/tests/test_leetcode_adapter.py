"""LeetCode adapter unit tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.agents.leetcode.adapter import to_analyze_response, to_coder_output, to_planner_output
from app.agents.leetcode.schemas import ProblemData
from app.models.enums import AIFeature, ExecutionMode, ModuleName, SessionStatus
from app.schemas.ai import ChatResponse, ModuleResponse, PlannerOutput as PlatformPlannerOutput


def test_to_coder_output_maps_structured_solutions() -> None:
    structured = {
        "brute_force": {
            "language": "python",
            "code": "def bf(): pass",
            "explanation": "nested loops",
        },
        "optimal_solution": {
            "language": "python",
            "code": "def opt(): pass",
            "complexity": "O(n)",
        },
    }
    output = to_coder_output(structured)
    assert output.brute_force is not None
    assert output.brute_force.code == "def bf(): pass"
    assert output.optimal is not None


def test_to_coder_output_maps_solutions_array() -> None:
    structured = {
        "language": "python",
        "solutions": [
            {"approach": "Brute Force", "code": "def bf(): pass"},
            {"approach": "Optimal", "code": "def opt(): pass"},
        ],
    }
    output = to_coder_output(structured)
    assert output.brute_force is not None
    assert output.better is not None


def test_to_analyze_response_maps_platform_chat() -> None:
    problem = ProblemData(
        title="Two Sum",
        slug="two-sum",
        url="https://leetcode.com/problems/two-sum/",
        description="Find two numbers.",
        difficulty="Easy",
        topics=["Array", "Hash Map"],
    )
    chat = ChatResponse(
        session_id=uuid4(),
        status=SessionStatus.COMPLETED,
        planner=PlatformPlannerOutput(
            feature=AIFeature.LEETCODE,
            modules=[ModuleName.TEACHER, ModuleName.CODER, ModuleName.EVALUATOR],
            execution_mode=ExecutionMode.SINGLE_LLM,
            metadata={
                "difficulty": "Easy",
                "problem_category": "Array",
                "patterns": ["Array", "Hash Map"],
                "execution_plan": ["Understand", "Solve"],
            },
        ),
        modules=[
            ModuleResponse(module=ModuleName.TEACHER, content="Explain complements."),
            ModuleResponse(
                module=ModuleName.CODER,
                content="code",
                structured={"optimal_solution": {"language": "python", "code": "pass"}},
            ),
            ModuleResponse(
                module=ModuleName.EVALUATOR,
                content="eval",
                structured={
                    "time_complexity": "O(n)",
                    "space_complexity": "O(n)",
                    "interview_questions": ["Duplicates?"],
                },
            ),
        ],
        total_tokens=120,
        execution_time_ms=400,
    )
    response = to_analyze_response(chat, problem)
    assert response.teacher == "Explain complements."
    assert response.planner.difficulty == "Easy"
    assert response.evaluator.interview_follow_ups == ["Duplicates?"]
    assert response.total_tokens == 120


def test_to_planner_output_uses_problem_fallback() -> None:
    problem = ProblemData(
        title="Two Sum",
        slug="two-sum",
        url="https://leetcode.com/problems/two-sum/",
        description="Find two numbers.",
        topics=["Hash Map"],
    )
    chat = ChatResponse(
        session_id=uuid4(),
        status=SessionStatus.COMPLETED,
        planner=PlatformPlannerOutput(
            feature=AIFeature.LEETCODE,
            modules=[ModuleName.TEACHER],
            execution_mode=ExecutionMode.SINGLE_LLM,
            metadata={},
        ),
        modules=[],
    )
    planner = to_planner_output(chat, problem)
    assert planner.patterns == ["Hash Map"]
    assert planner.problem_category == "Hash Map"
