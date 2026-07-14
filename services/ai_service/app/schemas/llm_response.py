"""Pydantic schemas for single-LLM structured JSON responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TeacherLLMOutput(BaseModel):
    """Teacher section returned by the LLM."""

    problem_summary: str = ""
    thinking_process: str = ""
    concepts: list[str] = Field(default_factory=list)
    learning_objectives: list[str] = Field(default_factory=list)
    approach: str = ""
    common_mistakes: list[str] = Field(default_factory=list)
    analogy: str = ""
    next_step: str = ""
    explanation: str = ""
    hints: list[str] = Field(default_factory=list)


class CodeSolution(BaseModel):
    """A single code solution with metadata."""

    language: str = "python"
    code: str = ""
    explanation: str = ""
    complexity: str = ""


class CoderLLMOutput(BaseModel):
    """Coder section returned by the LLM."""

    brute_force: CodeSolution | dict[str, Any] = Field(default_factory=dict)
    better_solution: CodeSolution | dict[str, Any] = Field(default_factory=dict)
    optimal_solution: CodeSolution | dict[str, Any] = Field(default_factory=dict)
    language: str = "python"
    solutions: list[dict[str, Any]] = Field(default_factory=list)


class EvaluatorLLMOutput(BaseModel):
    """Evaluator section returned by the LLM."""

    time_complexity: str = "Unknown"
    space_complexity: str = "Unknown"
    optimizations: list[str] = Field(default_factory=list)
    mistakes: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    interview_questions: list[str] = Field(default_factory=list)
    edge_cases: list[str] = Field(default_factory=list)
    feedback: str = ""
    analytics: dict[str, Any] = Field(default_factory=dict)


class CourseLLMOutput(BaseModel):
    """Learning-path section returned by the LLM (course generator)."""

    overview: dict[str, Any] = Field(default_factory=dict)
    roadmap: list[dict[str, Any]] = Field(default_factory=list)
    lessons: list[dict[str, Any]] = Field(default_factory=list)
    quizzes: list[dict[str, Any]] = Field(default_factory=list)
    assignments: list[dict[str, Any]] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    assessments: list[dict[str, Any]] = Field(default_factory=list)
    resources: list[dict[str, Any]] = Field(default_factory=list)
    learning_tips: list[str] = Field(default_factory=list)
    next_recommendations: list[str] = Field(default_factory=list)
    adaptive: dict[str, Any] = Field(default_factory=dict)


class DsaPatternLLMOutput(BaseModel):
    """DSA Pattern Coach section returned by the LLM."""

    overview: dict[str, Any] = Field(default_factory=dict)
    mental_model: dict[str, Any] = Field(default_factory=dict)
    recognition: dict[str, Any] = Field(default_factory=dict)
    visualization: dict[str, Any] = Field(default_factory=dict)
    templates: list[dict[str, Any]] = Field(default_factory=list)
    easy_example: dict[str, Any] = Field(default_factory=dict)
    medium_example: dict[str, Any] = Field(default_factory=dict)
    hard_example: dict[str, Any] = Field(default_factory=dict)
    common_mistakes: list[str] = Field(default_factory=list)
    interview_tips: dict[str, Any] = Field(default_factory=dict)
    pattern_comparison: list[dict[str, Any]] = Field(default_factory=list)
    practice: dict[str, Any] = Field(default_factory=dict)
    quiz: dict[str, Any] = Field(default_factory=dict)
    next_pattern_recommendation: dict[str, Any] = Field(default_factory=dict)


class UnifiedLLMResponse(BaseModel):
    """Shared response envelope from a single OpenRouter call.

    Processors consume teacher/coder/evaluator. Feature-specific payloads live in
    ``feature`` and are also projected onto legacy ``course`` / ``dsa_pattern``
    keys by the normalizer for existing adapters.
    """

    metadata: dict[str, Any] = Field(default_factory=dict)
    planner: dict[str, Any] = Field(default_factory=dict)
    teacher: TeacherLLMOutput = Field(default_factory=TeacherLLMOutput)
    coder: CoderLLMOutput = Field(default_factory=CoderLLMOutput)
    evaluator: EvaluatorLLMOutput = Field(default_factory=EvaluatorLLMOutput)
    feature: dict[str, Any] = Field(default_factory=dict)
    # Legacy projections kept for validation compatibility with older payloads.
    course: CourseLLMOutput | dict[str, Any] = Field(default_factory=dict)
    dsa_pattern: DsaPatternLLMOutput | dict[str, Any] = Field(default_factory=dict)
    interview: dict[str, Any] = Field(default_factory=dict)
