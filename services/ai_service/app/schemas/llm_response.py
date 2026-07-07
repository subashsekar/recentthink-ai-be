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


class UnifiedLLMResponse(BaseModel):
    """Complete structured JSON from a single OpenRouter call."""

    teacher: TeacherLLMOutput = Field(default_factory=TeacherLLMOutput)
    coder: CoderLLMOutput = Field(default_factory=CoderLLMOutput)
    evaluator: EvaluatorLLMOutput = Field(default_factory=EvaluatorLLMOutput)
