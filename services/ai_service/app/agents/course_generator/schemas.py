"""Pydantic schemas for the Learning Path / Course Generator API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import AgentName, MessageRole, SessionStatus


def _coerce_optional_str(value: object) -> str | None:
    """LLMs often return numeric ids; normalize to string."""
    if value is None:
        return None
    return str(value)


class GenerateCourseRequest(BaseModel):
    """Personalized learning-path generation request."""

    skill: str = Field(..., min_length=1, max_length=200)
    goal: str = Field(..., min_length=1, max_length=500, description="Target role or learning goal")
    level: str = Field(default="Beginner", max_length=50, description="Current skill level")
    target_level: str | None = Field(default=None, max_length=50)
    duration_days: int = Field(default=60, ge=7, le=365)
    daily_hours: float = Field(default=2.0, ge=0.5, le=12.0)
    learning_style: str = Field(default="Hands-on", max_length=100)
    language: str = Field(default="English", max_length=50, description="Instruction language")
    programming_language: str = Field(default="Python", max_length=50)
    topics_include: list[str] = Field(default_factory=list, max_length=30)
    topics_exclude: list[str] = Field(default_factory=list, max_length=30)
    output_format: Literal["full", "roadmap_only", "compact"] = "full"
    model_id: str | None = Field(default=None, max_length=255)
    mode_id: str | None = Field(default=None, max_length=50)
    requested_sections: list[str] | None = Field(
        default=None,
        description='Incremental generation, e.g. ["quiz", "project"].',
    )
    prior_response: dict | None = Field(
        default=None,
        description="Prior unified LLM payload for section reuse.",
    )

    @field_validator("skill", "goal", "level", "learning_style", "language", "programming_language")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("target_level", "model_id", "mode_id")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("topics_include", "topics_exclude")
    @classmethod
    def clean_topics(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item and item.strip()]


class CourseOverview(BaseModel):
    title: str = ""
    description: str = ""
    difficulty: str = ""
    estimated_duration_days: int | None = None
    estimated_study_hours: float | None = None
    learning_objectives: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    expected_outcomes: list[str] = Field(default_factory=list)


class DailyTopic(BaseModel):
    day: int | None = None
    topic: str = ""
    study_hours: float | None = None
    activity_type: str | None = None


class WeekRoadmap(BaseModel):
    week: int
    title: str = ""
    focus: str = ""
    daily_topics: list[DailyTopic] = Field(default_factory=list)
    study_hours: float | None = None
    milestones: list[str] = Field(default_factory=list)
    is_revision_week: bool = False
    is_project_week: bool = False
    is_assessment_week: bool = False


class LessonContent(BaseModel):
    id: str | None = None
    week: int | None = None
    title: str = ""
    objectives: list[str] = Field(default_factory=list)
    concept_explanation: str = ""
    examples: list[str] = Field(default_factory=list)
    visual_analogies: list[str] = Field(default_factory=list)
    common_mistakes: list[str] = Field(default_factory=list)
    best_practices: list[str] = Field(default_factory=list)
    summary: str = ""

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id(cls, value: object) -> str | None:
        return _coerce_optional_str(value)

    @field_validator("examples", "visual_analogies", "common_mistakes", "best_practices", "objectives", mode="before")
    @classmethod
    def coerce_str_list(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]


class QuizQuestion(BaseModel):
    type: str = "mcq"
    question: str = ""
    options: list[str] = Field(default_factory=list)
    answer: str = ""
    explanation: str = ""
    difficulty: str = "medium"

    @field_validator("answer", "question", "type", "explanation", "difficulty", mode="before")
    @classmethod
    def coerce_text(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value)

    @field_validator("options", mode="before")
    @classmethod
    def coerce_options(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]


class QuizContent(BaseModel):
    id: str | None = None
    week: int | None = None
    title: str = ""
    questions: list[QuizQuestion] = Field(default_factory=list)
    flashcards: list[dict[str, str]] = Field(default_factory=list)

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id(cls, value: object) -> str | None:
        return _coerce_optional_str(value)


class AssignmentContent(BaseModel):
    id: str | None = None
    week: int | None = None
    title: str = ""
    type: str = "weekly"
    description: str = ""
    tasks: list[str] = Field(default_factory=list)
    coding_exercises: list[str] = Field(default_factory=list)
    review_questions: list[str] = Field(default_factory=list)
    estimated_hours: float | None = None

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id(cls, value: object) -> str | None:
        return _coerce_optional_str(value)

    @field_validator("tasks", "coding_exercises", "review_questions", mode="before")
    @classmethod
    def coerce_str_list(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]


class ProjectContent(BaseModel):
    id: str | None = None
    title: str = ""
    level: str = "beginner"
    description: str = ""
    requirements: list[str] = Field(default_factory=list)
    architecture: str = ""
    implementation_steps: list[str] = Field(default_factory=list)
    expected_output: str = ""
    evaluation_criteria: list[str] = Field(default_factory=list)
    is_resume_project: bool = False

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id(cls, value: object) -> str | None:
        return _coerce_optional_str(value)

    @field_validator("requirements", "implementation_steps", "evaluation_criteria", mode="before")
    @classmethod
    def coerce_str_list(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]


class AssessmentContent(BaseModel):
    id: str | None = None
    week: int | None = None
    title: str = ""
    type: str = "weekly"
    questions: list[str] = Field(default_factory=list)
    rubric: list[str] = Field(default_factory=list)
    scoring: str = ""
    completion_criteria: list[str] = Field(default_factory=list)

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id(cls, value: object) -> str | None:
        return _coerce_optional_str(value)

    @field_validator("questions", "rubric", "completion_criteria", mode="before")
    @classmethod
    def coerce_str_list(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]

    @field_validator("scoring", mode="before")
    @classmethod
    def coerce_scoring(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value)


class ResourceItem(BaseModel):
    title: str = ""
    type: str = "article"
    url: str | None = None
    description: str = ""
    week: int | None = None


class AdaptiveRecommendations(BaseModel):
    """Adaptive learning hints based on performance signals."""

    struggling: list[str] = Field(
        default_factory=list,
        description="Extra lessons, practice, simplified examples when scoring poorly",
    )
    excelling: list[str] = Field(
        default_factory=list,
        description="Skip basics, unlock advanced content, larger projects when performing well",
    )


class CourseContent(BaseModel):
    """Full structured learning path from a single OpenRouter response."""

    overview: CourseOverview = Field(default_factory=CourseOverview)
    roadmap: list[WeekRoadmap] = Field(default_factory=list)
    lessons: list[LessonContent] = Field(default_factory=list)
    quizzes: list[QuizContent] = Field(default_factory=list)
    assignments: list[AssignmentContent] = Field(default_factory=list)
    projects: list[ProjectContent] = Field(default_factory=list)
    assessments: list[AssessmentContent] = Field(default_factory=list)
    resources: list[ResourceItem] = Field(default_factory=list)
    learning_tips: list[str] = Field(default_factory=list)
    next_recommendations: list[str] = Field(default_factory=list)
    adaptive: AdaptiveRecommendations = Field(default_factory=AdaptiveRecommendations)


class PlannerOutput(BaseModel):
    skill: str
    goal: str
    difficulty: str
    duration_days: int
    daily_hours: float
    estimated_study_hours: float
    learning_objectives: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    roadmap_outline: list[str] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)
    execution_plan: list[str] = Field(default_factory=list)


class CourseProgressSnapshot(BaseModel):
    course_id: UUID | None = None
    current_week: int = 1
    current_lesson: int = 0
    completion_pct: float = 0.0
    lessons_completed: int = 0
    quizzes_completed: int = 0
    projects_completed: int = 0
    study_hours: float = 0.0


class UsageSummary(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    execution_time_ms: int = 0
    estimated_cost: float = 0.0
    model: str | None = None
    feature: str = "course_generator"


class TraceNode(BaseModel):
    node: str
    status: str = "SUCCESS"


class GenerateCourseResponse(BaseModel):
    """Frontend-ready course generation response."""

    session_id: UUID
    course_id: UUID
    status: SessionStatus
    mode_id: str | None = None
    request: GenerateCourseRequest
    planner: PlannerOutput
    overview: CourseOverview
    roadmap: list[WeekRoadmap] = Field(default_factory=list)
    lessons: list[LessonContent] = Field(default_factory=list)
    quizzes: list[QuizContent] = Field(default_factory=list)
    assignments: list[AssignmentContent] = Field(default_factory=list)
    projects: list[ProjectContent] = Field(default_factory=list)
    assessments: list[AssessmentContent] = Field(default_factory=list)
    resources: list[ResourceItem] = Field(default_factory=list)
    learning_tips: list[str] = Field(default_factory=list)
    next_recommendations: list[str] = Field(default_factory=list)
    adaptive: AdaptiveRecommendations = Field(default_factory=AdaptiveRecommendations)
    teacher_summary: str = ""
    progress: CourseProgressSnapshot = Field(default_factory=CourseProgressSnapshot)
    usage: UsageSummary = Field(default_factory=UsageSummary)
    execution_trace: list[TraceNode] = Field(default_factory=list)


class FollowUpRequest(BaseModel):
    session_id: UUID
    question: str = Field(..., min_length=1, max_length=8000)
    model: str | None = Field(default=None, max_length=255)
    mode_id: str | None = Field(default=None, max_length=50)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=32000)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        return value.strip()


class FollowUpResponse(BaseModel):
    session_id: UUID
    intent: str
    teacher: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    execution_time_ms: int = 0
    context_match: bool = True
    rejected: bool = False


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: MessageRole
    agent_name: AgentName | None
    message: str
    created_at: datetime


class CourseHistoryItem(BaseModel):
    course_id: UUID
    session_id: UUID
    title: str
    skill: str | None = None
    goal: str | None = None
    level: str | None = None
    status: SessionStatus
    model_id: str | None = None
    completion_pct: float = 0.0
    preview: str | None = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class CourseHistoryListResponse(BaseModel):
    items: list[CourseHistoryItem]
    page: int
    page_size: int
    total: int


class CourseChatHistoryDetailResponse(BaseModel):
    """Static chat history for one course — mentor-style thread + course snapshot."""

    course_id: UUID
    session_id: UUID
    title: str | None = None
    skill: str | None = None
    goal: str | None = None
    level: str | None = None
    status: SessionStatus
    model_id: str | None = None
    mode_id: str | None = None
    messages: list[ChatMessageResponse] = Field(default_factory=list)
    total_messages: int = 0
    content: CourseContent | None = None
    created_at: datetime
    updated_at: datetime


class SessionDetailResponse(BaseModel):
    course_id: UUID | None = None
    session_id: UUID
    title: str | None = None
    skill: str | None = None
    goal: str | None = None
    level: str | None = None
    status: SessionStatus
    model_id: str | None = None
    mode_id: str | None = None
    content: CourseContent | None = None
    messages: list[ChatMessageResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

class ProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    courses_created: int
    courses_completed: int
    lessons_completed: int
    projects_completed: int
    quizzes_completed: int
    current_week: int
    current_lesson: int
    completion_pct: float
    learning_streak: int
    longest_streak: int
    study_hours: float
    favorite_skill: str | None = None
    skills: list[str] = Field(default_factory=list)
    updated_at: datetime


class DashboardResponse(BaseModel):
    progress: ProgressResponse
    recent_courses: list[CourseHistoryItem] = Field(default_factory=list)
    active_course: CourseHistoryItem | None = None


class UpdateProgressRequest(BaseModel):
    course_id: UUID
    current_week: int | None = Field(default=None, ge=1)
    current_lesson: int | None = Field(default=None, ge=0)
    lessons_completed_delta: int = Field(default=0, ge=0)
    quizzes_completed_delta: int = Field(default=0, ge=0)
    projects_completed_delta: int = Field(default=0, ge=0)
    study_hours_delta: float = Field(default=0.0, ge=0.0)
    completion_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    mark_completed: bool = False


class BookmarkRequest(BaseModel):
    course_id: UUID
    item_type: str = Field(..., min_length=1, max_length=50)
    item_id: str = Field(..., min_length=1, max_length=100)
    title: str | None = Field(default=None, max_length=500)


class BookmarkResponse(BaseModel):
    id: UUID
    course_id: UUID
    item_type: str
    item_id: str
    title: str | None = None
    created_at: datetime


class ExportRequest(BaseModel):
    course_id: UUID
    include: list[str] = Field(
        default_factory=lambda: [
            "roadmap",
            "lessons",
            "projects",
            "assignments",
            "quiz",
            "assessment",
            "resources",
        ],
    )


class ExportResponse(BaseModel):
    course_id: UUID
    format: str
    filename: str
    content: str
    content_type: str


class CourseExampleResponse(BaseModel):
    id: str
    title: str
    skill: str
    goal: str
    level: str
    duration_days: int
    daily_hours: float
    learning_style: str
    programming_language: str
    icon: str | None = None


class CourseAgentInfoResponse(BaseModel):
    role: str
    name: str
    description: str
    uses_openrouter: bool
    workflow_module: str | None = None
    prompt_module: str | None = None
    shared_path: str


class VersionHistoryItem(BaseModel):
    message_id: UUID
    created_at: datetime
    status: str
    regenerated_from_message_id: UUID | None = None
    is_current: bool


class DeleteCourseResponse(BaseModel):
    message: str = "Course deleted successfully."


class AdaptiveFeedbackRequest(BaseModel):
    """Record quiz/assessment performance to drive adaptive recommendations."""

    course_id: UUID
    score_pct: float = Field(..., ge=0.0, le=100.0)
    week: int | None = Field(default=None, ge=1)
    topic: str | None = None


class AdaptiveFeedbackResponse(BaseModel):
    course_id: UUID
    performance: Literal["struggling", "on_track", "excelling"]
    recommendations: list[str] = Field(default_factory=list)
    unlock_advanced: bool = False
    skip_basics: bool = False
