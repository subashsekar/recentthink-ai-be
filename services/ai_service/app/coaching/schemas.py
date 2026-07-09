"""Coaching mode schemas (first-class mode configs).

Modes are similar to models: a small, validated catalog drives prompt choice,
planner behavior, and generation settings across the pipeline.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


DetailLevel = Literal["low", "medium", "high"]
Strictness = Literal["low", "medium", "high"]


class GenerationSettings(BaseModel):
    """Default generation settings for a coaching mode.

    Individual requests may override some values (e.g. follow-up max_tokens).
    """

    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=32000)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    frequency_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)
    presence_penalty: float | None = Field(default=None, ge=-2.0, le=2.0)


class PlannerSettings(BaseModel):
    """Planner behavior controls (deterministic planner uses these as hints)."""

    detail_level: DetailLevel = "medium"
    include_examples: bool = True
    focus_complexity: bool = True
    include_multiple_approaches: bool = True


class TeacherSettings(BaseModel):
    """Teacher behavior controls (primarily prompt + formatting)."""

    style: str = "educational"
    show_hints: bool = True
    reveal_answer: bool = True
    ask_questions: bool = False
    include_similar_problems: bool = False


class EvaluatorSettings(BaseModel):
    """Evaluator behavior controls (primarily prompt)."""

    strictness: Strictness = "medium"
    verbosity: DetailLevel = "medium"


class ModeMetadata(BaseModel):
    """Frontend-facing metadata for a coaching mode."""

    id: str = Field(min_length=1, max_length=50)
    label: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    icon: str = Field(default="", max_length=50)
    recommended: bool = False


class ModeConfig(BaseModel):
    """Resolved mode config consumed by the pipeline."""

    metadata: ModeMetadata
    generation: GenerationSettings = Field(default_factory=GenerationSettings)
    planner: PlannerSettings = Field(default_factory=PlannerSettings)
    teacher: TeacherSettings = Field(default_factory=TeacherSettings)
    evaluator: EvaluatorSettings = Field(default_factory=EvaluatorSettings)

    # Prompt templates (paths are resolved by ModePromptLoader).
    analyze_prompt: str = Field(default="", description="Mode-specific analyze prompt template id.")
    followup_prompt: str = Field(default="", description="Mode-specific follow-up prompt template id.")

    extra: dict[str, Any] = Field(default_factory=dict)

