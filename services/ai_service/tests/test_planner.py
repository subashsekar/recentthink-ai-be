"""Planner unit tests."""

from __future__ import annotations

import pytest
from app.agents.shared.planner.planner import Planner
from app.models.enums import AIFeature, ExecutionMode, ModuleName
from app.schemas.ai import ChatRequest
from shared.exceptions.base import ValidationException


@pytest.fixture
def planner() -> Planner:
    return Planner()


def test_plan_leetcode_modules(planner: Planner) -> None:
    request = ChatRequest(feature=AIFeature.LEETCODE, message="Solve two sum")
    output = planner.plan(request)
    assert output.feature == AIFeature.LEETCODE
    assert output.execution_mode == ExecutionMode.SINGLE_LLM
    assert ModuleName.TEACHER in output.modules
    assert ModuleName.CODER in output.modules
    assert ModuleName.CODE_EXPLAINER in output.modules
    assert ModuleName.EVALUATOR in output.modules
    assert output.modules.index(ModuleName.CODER) < output.modules.index(ModuleName.CODE_EXPLAINER)
    assert output.modules.index(ModuleName.CODE_EXPLAINER) < output.modules.index(ModuleName.EVALUATOR)


def test_plan_dsa_modules(planner: Planner) -> None:
    request = ChatRequest(feature=AIFeature.DSA, message="Explain binary search")
    output = planner.plan(request)
    assert ModuleName.CODER not in output.modules
    assert ModuleName.TEACHER in output.modules


def test_plan_rejects_empty_message(planner: Planner) -> None:
    request = ChatRequest(feature=AIFeature.LEETCODE, message="   ")
    with pytest.raises(ValidationException):
        planner.plan(request)


def test_classify_message(planner: Planner) -> None:
    assert planner.classify_message("implement the solution in code") == "coding"
    assert planner.classify_message("explain the concept") == "teaching"
    assert planner.classify_message("what is the time complexity") == "evaluation"
    assert planner.classify_message("hello") == "general"


def test_resolve_feature_alias() -> None:
    assert Planner.resolve_feature_alias("dsa_tutor") == AIFeature.DSA
    assert Planner.resolve_feature_alias("dsa_pattern") == AIFeature.DSA_PATTERN
    assert Planner.resolve_feature_alias("dsa-pattern") == AIFeature.DSA_PATTERN


def test_plan_dsa_pattern_modules(planner: Planner) -> None:
    request = ChatRequest(
        feature=AIFeature.DSA_PATTERN,
        message="Teach Sliding Window",
        context={
            "pattern": "Sliding Window",
            "level": "Beginner",
            "language": "Python",
            "learning_style": "Visual",
        },
    )
    output = planner.plan(request)
    assert output.feature == AIFeature.DSA_PATTERN
    assert output.modules == [ModuleName.TEACHER]
    assert ModuleName.CODER not in output.modules
    assert output.metadata["pattern"] == "Sliding Window"
    assert output.metadata["estimated_study_time"]
    assert len(output.metadata["learning_objectives"]) >= 3
    assert len(output.metadata["execution_plan"]) >= 3


def test_plan_leetcode_metadata_from_context(planner: Planner) -> None:
    request = ChatRequest(
        feature=AIFeature.LEETCODE,
        message="Analyze two sum",
        context={
            "title": "Two Sum",
            "slug": "two-sum",
            "url": "https://leetcode.com/problems/two-sum/",
            "description": "Find two numbers in an array.",
            "difficulty": "Easy",
            "topics": ["Array", "Hash Map"],
        },
    )
    output = planner.plan(request)
    assert output.metadata["difficulty"] == "Easy"
    assert output.metadata["problem_category"] == "Array"
    assert "Hash Map" in output.metadata["patterns"]
    assert len(output.metadata["execution_plan"]) >= 3
