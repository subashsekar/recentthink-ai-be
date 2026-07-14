"""DSA Pattern Coach pipeline agent declarations (feature adapter over shared platform)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.agents.shared.planner.planner import Planner
from app.agents.shared.teacher.module import TeacherModule
from app.models.enums import AIFeature, ModuleName


class PatternAgentRole(StrEnum):
    PLANNER = "planner"
    LEARNING = "learning_agent"
    RECOGNITION = "recognition_agent"
    VISUALIZATION = "visualization_agent"
    TEMPLATE = "template_agent"
    WALKTHROUGH = "problem_walkthrough_agent"
    PRACTICE = "practice_agent"
    QUIZ = "quiz_agent"
    PROGRESS = "progress_coach"
    TEACHER = "teacher"


@dataclass(frozen=True)
class PatternAgentSpec:
    role: PatternAgentRole
    name: str
    description: str
    uses_openrouter: bool
    workflow_module: ModuleName | None
    prompt_module: str | None
    shared_path: str


PATTERN_AGENT_SPECS: tuple[PatternAgentSpec, ...] = (
    PatternAgentSpec(
        role=PatternAgentRole.PLANNER,
        name="Pattern Planner",
        description="Deterministic category, difficulty, prerequisites, study time, objectives, roadmap.",
        uses_openrouter=False,
        workflow_module=ModuleName.PLANNER,
        prompt_module="planner",
        shared_path="app.agents.shared.planner.planner.Planner",
    ),
    PatternAgentSpec(
        role=PatternAgentRole.LEARNING,
        name="Learning Agent",
        description="Pattern overview + mental model inside the single OpenRouter JSON (dsa_pattern.overview).",
        uses_openrouter=False,
        workflow_module=ModuleName.OPENROUTER,
        prompt_module="master",
        shared_path="app.prompts.features.dsa_pattern",
    ),
    PatternAgentSpec(
        role=PatternAgentRole.RECOGNITION,
        name="Recognition Agent",
        description="How to identify the pattern (keywords, signals, checklist) in dsa_pattern.recognition.",
        uses_openrouter=False,
        workflow_module=ModuleName.OPENROUTER,
        prompt_module="master",
        shared_path="app.prompts.features.dsa_pattern",
    ),
    PatternAgentSpec(
        role=PatternAgentRole.VISUALIZATION,
        name="Visualization Agent",
        description="ASCII diagrams and step-by-step visuals in dsa_pattern.visualization.",
        uses_openrouter=False,
        workflow_module=ModuleName.OPENROUTER,
        prompt_module="master",
        shared_path="app.prompts.features.dsa_pattern",
    ),
    PatternAgentSpec(
        role=PatternAgentRole.TEMPLATE,
        name="Template Agent",
        description="Reusable multi-language templates in dsa_pattern.templates (not problem-specific).",
        uses_openrouter=False,
        workflow_module=ModuleName.OPENROUTER,
        prompt_module="master",
        shared_path="app.prompts.features.dsa_pattern",
    ),
    PatternAgentSpec(
        role=PatternAgentRole.WALKTHROUGH,
        name="Problem Walkthrough Agent",
        description="Easy/medium/hard worked examples in dsa_pattern.*_example.",
        uses_openrouter=False,
        workflow_module=ModuleName.OPENROUTER,
        prompt_module="master",
        shared_path="app.prompts.features.dsa_pattern",
    ),
    PatternAgentSpec(
        role=PatternAgentRole.PRACTICE,
        name="Practice Agent",
        description="Practice roadmap and problem sets in dsa_pattern.practice.",
        uses_openrouter=False,
        workflow_module=ModuleName.OPENROUTER,
        prompt_module="master",
        shared_path="app.prompts.features.dsa_pattern",
    ),
    PatternAgentSpec(
        role=PatternAgentRole.QUIZ,
        name="Quiz Agent",
        description="MCQs, recognition/scenario/coding questions, flashcards in dsa_pattern.quiz.",
        uses_openrouter=False,
        workflow_module=ModuleName.OPENROUTER,
        prompt_module="master",
        shared_path="app.prompts.features.dsa_pattern",
    ),
    PatternAgentSpec(
        role=PatternAgentRole.PROGRESS,
        name="Progress Coach",
        description="Tracks mastery via pattern_progress / pattern_mastery (no extra LLM call).",
        uses_openrouter=False,
        workflow_module=ModuleName.PERSIST,
        prompt_module=None,
        shared_path="app.repositories.dsa_pattern_repository.PatternProgressRepository",
    ),
    PatternAgentSpec(
        role=PatternAgentRole.TEACHER,
        name="Teacher",
        description="Formats pattern narrative from unified LLM JSON. No extra LLM call.",
        uses_openrouter=False,
        workflow_module=ModuleName.TEACHER,
        prompt_module="teacher",
        shared_path="app.agents.shared.teacher.module.TeacherModule",
    ),
)


@dataclass
class PatternAgents:
    planner: Planner
    teacher: TeacherModule

    @classmethod
    def create_default(cls) -> PatternAgents:
        return cls(planner=Planner(), teacher=TeacherModule())

    def get(self, role: PatternAgentRole) -> Any:
        mapping: dict[PatternAgentRole, Any] = {
            PatternAgentRole.PLANNER: self.planner,
            PatternAgentRole.TEACHER: self.teacher,
        }
        return mapping.get(role)

    @staticmethod
    def list_specs() -> list[PatternAgentSpec]:
        return list(PATTERN_AGENT_SPECS)


DSA_PATTERN_FEATURE = AIFeature.DSA_PATTERN
DSA_PATTERN_OPENROUTER_PROMPT = "master"
