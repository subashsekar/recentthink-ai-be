"""Course Generator pipeline agent declarations (feature adapter over shared platform)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.agents.shared.planner.planner import Planner
from app.agents.shared.teacher.module import TeacherModule
from app.models.enums import AIFeature, ModuleName


class CourseAgentRole(StrEnum):
    PLANNER = "planner"
    COURSE_GENERATOR = "course_generator"
    ROADMAP_GENERATOR = "roadmap_generator"
    LESSON_GENERATOR = "lesson_generator"
    QUIZ_GENERATOR = "quiz_generator"
    ASSIGNMENT_GENERATOR = "assignment_generator"
    PROJECT_GENERATOR = "project_generator"
    ASSESSMENT_GENERATOR = "assessment_generator"
    TEACHER = "teacher"


@dataclass(frozen=True)
class CourseAgentSpec:
    role: CourseAgentRole
    name: str
    description: str
    uses_openrouter: bool
    workflow_module: ModuleName | None
    prompt_module: str | None
    shared_path: str


COURSE_AGENT_SPECS: tuple[CourseAgentSpec, ...] = (
    CourseAgentSpec(
        role=CourseAgentRole.PLANNER,
        name="Planner",
        description="Deterministic course structure, objectives, milestones, and time budget.",
        uses_openrouter=False,
        workflow_module=ModuleName.PLANNER,
        prompt_module="planner",
        shared_path="app.agents.shared.planner.planner.Planner",
    ),
    CourseAgentSpec(
        role=CourseAgentRole.COURSE_GENERATOR,
        name="Course Generator",
        description="Logical stage inside the single OpenRouter JSON (course.overview).",
        uses_openrouter=False,
        workflow_module=ModuleName.OPENROUTER,
        prompt_module="master",
        shared_path="app.prompts.features.course_generator",
    ),
    CourseAgentSpec(
        role=CourseAgentRole.ROADMAP_GENERATOR,
        name="Roadmap Generator",
        description="Week-wise roadmap inside the single OpenRouter JSON (course.roadmap).",
        uses_openrouter=False,
        workflow_module=ModuleName.OPENROUTER,
        prompt_module="master",
        shared_path="app.prompts.features.course_generator",
    ),
    CourseAgentSpec(
        role=CourseAgentRole.LESSON_GENERATOR,
        name="Lesson Generator",
        description="Lessons inside the single OpenRouter JSON (course.lessons).",
        uses_openrouter=False,
        workflow_module=ModuleName.OPENROUTER,
        prompt_module="master",
        shared_path="app.prompts.features.course_generator",
    ),
    CourseAgentSpec(
        role=CourseAgentRole.QUIZ_GENERATOR,
        name="Quiz Generator",
        description="Quizzes and flashcards inside the single OpenRouter JSON (course.quizzes).",
        uses_openrouter=False,
        workflow_module=ModuleName.OPENROUTER,
        prompt_module="master",
        shared_path="app.prompts.features.course_generator",
    ),
    CourseAgentSpec(
        role=CourseAgentRole.ASSIGNMENT_GENERATOR,
        name="Assignment Generator",
        description="Assignments inside the single OpenRouter JSON (course.assignments).",
        uses_openrouter=False,
        workflow_module=ModuleName.OPENROUTER,
        prompt_module="master",
        shared_path="app.prompts.features.course_generator",
    ),
    CourseAgentSpec(
        role=CourseAgentRole.PROJECT_GENERATOR,
        name="Project Generator",
        description="Projects inside the single OpenRouter JSON (course.projects).",
        uses_openrouter=False,
        workflow_module=ModuleName.OPENROUTER,
        prompt_module="master",
        shared_path="app.prompts.features.course_generator",
    ),
    CourseAgentSpec(
        role=CourseAgentRole.ASSESSMENT_GENERATOR,
        name="Assessment Generator",
        description="Assessments inside the single OpenRouter JSON (course.assessments).",
        uses_openrouter=False,
        workflow_module=ModuleName.OPENROUTER,
        prompt_module="master",
        shared_path="app.prompts.features.course_generator",
    ),
    CourseAgentSpec(
        role=CourseAgentRole.TEACHER,
        name="Teacher",
        description="Formats course overview narrative from unified LLM JSON. No extra LLM call.",
        uses_openrouter=False,
        workflow_module=ModuleName.TEACHER,
        prompt_module="teacher",
        shared_path="app.agents.shared.teacher.module.TeacherModule",
    ),
)


@dataclass
class CourseAgents:
    planner: Planner
    teacher: TeacherModule

    @classmethod
    def create_default(cls) -> CourseAgents:
        return cls(planner=Planner(), teacher=TeacherModule())

    def get(self, role: CourseAgentRole) -> Any:
        mapping: dict[CourseAgentRole, Any] = {
            CourseAgentRole.PLANNER: self.planner,
            CourseAgentRole.TEACHER: self.teacher,
        }
        return mapping.get(role)

    @staticmethod
    def list_specs() -> list[CourseAgentSpec]:
        return list(COURSE_AGENT_SPECS)


COURSE_FEATURE = AIFeature.COURSE_GENERATOR
COURSE_OPENROUTER_PROMPT = "master"
