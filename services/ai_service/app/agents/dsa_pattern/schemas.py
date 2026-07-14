"""Pydantic schemas for the DSA Pattern Coach API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AgentName, MessageRole, SessionStatus


def _coerce_str_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


class GeneratePatternRequest(BaseModel):
    """Pattern-centric learning request."""

    pattern: str = Field(..., min_length=1, max_length=200, description="DSA pattern name")
    level: str = Field(default="Beginner", max_length=50)
    language: str = Field(default="Python", max_length=50, description="Preferred programming language")
    learning_style: str = Field(default="Visual", max_length=100)
    model_id: str | None = Field(default=None, max_length=255)
    mode_id: str | None = Field(default=None, max_length=50)
    requested_sections: list[str] | None = Field(
        default=None,
        description='Incremental generation, e.g. ["recognition", "practice"].',
    )
    prior_response: dict | None = Field(
        default=None,
        description="Prior unified LLM payload for section reuse.",
    )

    @field_validator("pattern", "level", "language", "learning_style")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("model_id", "mode_id")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class PatternOverview(BaseModel):
    pattern: str = ""
    definition: str = ""
    history: str = ""
    why_it_exists: str = ""
    real_world_use_cases: list[str] = Field(default_factory=list)
    category: str = ""
    difficulty: str = ""
    prerequisites: list[str] = Field(default_factory=list)
    estimated_study_time: str = ""
    learning_objectives: list[str] = Field(default_factory=list)
    beginner_explanation: str = ""
    intermediate_explanation: str = ""
    advanced_explanation: str = ""

    @field_validator("real_world_use_cases", "prerequisites", "learning_objectives", mode="before")
    @classmethod
    def coerce_lists(cls, value: object) -> list[str]:
        return _coerce_str_list(value)


class MentalModel(BaseModel):
    summary: str = ""
    analogies: list[str] = Field(default_factory=list)
    key_insights: list[str] = Field(default_factory=list)
    intuition: str = ""

    @field_validator("analogies", "key_insights", mode="before")
    @classmethod
    def coerce_lists(cls, value: object) -> list[str]:
        return _coerce_str_list(value)


class RecognitionGuide(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)
    recognition_rules: list[str] = Field(default_factory=list)
    decision_tree: list[str] = Field(default_factory=list)
    common_clues: list[str] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)
    how_to_identify: str = ""

    @field_validator(
        "keywords",
        "signals",
        "recognition_rules",
        "decision_tree",
        "common_clues",
        "checklist",
        mode="before",
    )
    @classmethod
    def coerce_lists(cls, value: object) -> list[str]:
        return _coerce_str_list(value)


class VisualizationContent(BaseModel):
    ascii_diagrams: list[str] = Field(default_factory=list)
    step_by_step: list[str] = Field(default_factory=list)
    pointer_animation: str = ""
    array_visualization: str = ""
    graph_visualization: str = ""
    tree_visualization: str = ""
    recursion_stack: str = ""
    queue_evolution: str = ""
    stack_evolution: str = ""
    frontend_notes: str = ""

    @field_validator("ascii_diagrams", "step_by_step", mode="before")
    @classmethod
    def coerce_lists(cls, value: object) -> list[str]:
        return _coerce_str_list(value)


class CodeTemplate(BaseModel):
    language: str = "python"
    template: str = ""
    description: str = ""
    when_to_use: str = ""


class WalkthroughExample(BaseModel):
    difficulty: str = "easy"
    title: str = ""
    problem_statement: str = ""
    pattern_recognition: str = ""
    approach: str = ""
    dry_run: list[str] = Field(default_factory=list)
    visualization: str = ""
    code: str = ""
    language: str = "python"
    line_by_line: list[str] = Field(default_factory=list)
    time_complexity: str = ""
    space_complexity: str = ""
    edge_cases: list[str] = Field(default_factory=list)
    common_mistakes: list[str] = Field(default_factory=list)

    @field_validator("dry_run", "line_by_line", "edge_cases", "common_mistakes", mode="before")
    @classmethod
    def coerce_lists(cls, value: object) -> list[str]:
        return _coerce_str_list(value)


class InterviewTips(BaseModel):
    interview_questions: list[str] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    expected_thought_process: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    optimization_discussion: list[str] = Field(default_factory=list)

    @field_validator(
        "interview_questions",
        "hints",
        "expected_thought_process",
        "follow_up_questions",
        "optimization_discussion",
        mode="before",
    )
    @classmethod
    def coerce_lists(cls, value: object) -> list[str]:
        return _coerce_str_list(value)


class PatternComparisonItem(BaseModel):
    other_pattern: str = ""
    when_to_choose_this: str = ""
    when_to_choose_other: str = ""
    key_differences: list[str] = Field(default_factory=list)
    summary: str = ""

    @field_validator("key_differences", mode="before")
    @classmethod
    def coerce_lists(cls, value: object) -> list[str]:
        return _coerce_str_list(value)


class PracticeProblem(BaseModel):
    title: str = ""
    difficulty: str = "easy"
    platform: str = ""
    url: str | None = None
    why: str = ""
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags", mode="before")
    @classmethod
    def coerce_lists(cls, value: object) -> list[str]:
        return _coerce_str_list(value)


class PracticeContent(BaseModel):
    roadmap: list[str] = Field(default_factory=list)
    easy: list[PracticeProblem] = Field(default_factory=list)
    medium: list[PracticeProblem] = Field(default_factory=list)
    hard: list[PracticeProblem] = Field(default_factory=list)
    interview: list[PracticeProblem] = Field(default_factory=list)
    contest: list[PracticeProblem] = Field(default_factory=list)
    revision: list[PracticeProblem] = Field(default_factory=list)

    @field_validator("roadmap", mode="before")
    @classmethod
    def coerce_roadmap(cls, value: object) -> list[str]:
        return _coerce_str_list(value)


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
        return _coerce_str_list(value)


class QuizContent(BaseModel):
    title: str = ""
    mcqs: list[QuizQuestion] = Field(default_factory=list)
    recognition_questions: list[QuizQuestion] = Field(default_factory=list)
    scenario_questions: list[QuizQuestion] = Field(default_factory=list)
    coding_questions: list[QuizQuestion] = Field(default_factory=list)
    flashcards: list[dict[str, str]] = Field(default_factory=list)
    mini_assessment: list[QuizQuestion] = Field(default_factory=list)


class NextPatternRecommendation(BaseModel):
    pattern: str = ""
    reason: str = ""
    prerequisites_met: bool = True
    estimated_study_time: str = ""


class PatternContent(BaseModel):
    """Full structured pattern lesson from a single OpenRouter response."""

    overview: PatternOverview = Field(default_factory=PatternOverview)
    mental_model: MentalModel = Field(default_factory=MentalModel)
    recognition: RecognitionGuide = Field(default_factory=RecognitionGuide)
    visualization: VisualizationContent = Field(default_factory=VisualizationContent)
    templates: list[CodeTemplate] = Field(default_factory=list)
    easy_example: WalkthroughExample = Field(default_factory=WalkthroughExample)
    medium_example: WalkthroughExample = Field(default_factory=WalkthroughExample)
    hard_example: WalkthroughExample = Field(default_factory=WalkthroughExample)
    common_mistakes: list[str] = Field(default_factory=list)
    interview_tips: InterviewTips = Field(default_factory=InterviewTips)
    pattern_comparison: list[PatternComparisonItem] = Field(default_factory=list)
    practice: PracticeContent = Field(default_factory=PracticeContent)
    quiz: QuizContent = Field(default_factory=QuizContent)
    next_pattern_recommendation: NextPatternRecommendation = Field(default_factory=NextPatternRecommendation)

    @field_validator("common_mistakes", mode="before")
    @classmethod
    def coerce_mistakes(cls, value: object) -> list[str]:
        return _coerce_str_list(value)


class PlannerOutput(BaseModel):
    pattern: str
    category: str
    difficulty: str
    prerequisites: list[str] = Field(default_factory=list)
    estimated_study_time: str = ""
    learning_objectives: list[str] = Field(default_factory=list)
    roadmap: list[str] = Field(default_factory=list)
    execution_plan: list[str] = Field(default_factory=list)


class PatternProgressSnapshot(BaseModel):
    pattern_session_id: UUID | None = None
    completion_pct: float = 0.0
    practice_completed: int = 0
    quiz_score: float | None = None
    study_minutes: int = 0


class UsageSummary(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    execution_time_ms: int = 0
    estimated_cost: float = 0.0
    model: str | None = None
    feature: str = "dsa_pattern"


class TraceNode(BaseModel):
    node: str
    status: str = "SUCCESS"


class GeneratePatternResponse(BaseModel):
    """Frontend-ready DSA pattern coach response."""

    session_id: UUID
    pattern_session_id: UUID
    status: SessionStatus
    mode_id: str | None = None
    request: GeneratePatternRequest
    planner: PlannerOutput
    overview: PatternOverview
    mental_model: MentalModel
    recognition: RecognitionGuide
    visualization: VisualizationContent
    templates: list[CodeTemplate] = Field(default_factory=list)
    easy_example: WalkthroughExample
    medium_example: WalkthroughExample
    hard_example: WalkthroughExample
    common_mistakes: list[str] = Field(default_factory=list)
    interview_tips: InterviewTips
    pattern_comparison: list[PatternComparisonItem] = Field(default_factory=list)
    practice: PracticeContent
    quiz: QuizContent
    next_pattern_recommendation: NextPatternRecommendation
    teacher_summary: str = ""
    progress: PatternProgressSnapshot = Field(default_factory=PatternProgressSnapshot)
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


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: MessageRole
    agent_name: AgentName | None
    message: str
    created_at: datetime


class PatternHistoryItem(BaseModel):
    pattern_session_id: UUID
    session_id: UUID
    title: str
    pattern: str
    level: str | None = None
    language: str | None = None
    status: SessionStatus
    model_id: str | None = None
    completion_pct: float = 0.0
    preview: str | None = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class PatternHistoryListResponse(BaseModel):
    items: list[PatternHistoryItem]
    page: int
    page_size: int
    total: int


class SessionDetailResponse(BaseModel):
    pattern_session_id: UUID | None = None
    session_id: UUID
    title: str | None = None
    pattern: str | None = None
    level: str | None = None
    language: str | None = None
    status: SessionStatus
    model_id: str | None = None
    mode_id: str | None = None
    content: PatternContent | None = None
    messages: list[ChatMessageResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class MasteryItem(BaseModel):
    pattern_name: str
    status: str
    sessions_count: int = 0
    practice_completed: int = 0
    quiz_attempts: int = 0
    best_quiz_score: float = 0.0
    mastery_pct: float = 0.0
    last_studied_at: datetime | None = None


class ProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    patterns_learned: int
    patterns_mastered: int
    practice_completed: int
    quizzes_completed: int
    average_quiz_score: float
    current_streak: int
    longest_streak: int
    learning_time_minutes: int
    recommended_next_pattern: str | None = None
    weak_patterns: list[str] = Field(default_factory=list)
    strong_patterns: list[str] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)
    mastery: list[MasteryItem] = Field(default_factory=list)
    updated_at: datetime


class DashboardResponse(BaseModel):
    progress: ProgressResponse
    recent_sessions: list[PatternHistoryItem] = Field(default_factory=list)
    active_session: PatternHistoryItem | None = None


class UpdateProgressRequest(BaseModel):
    pattern_session_id: UUID
    practice_completed_delta: int = Field(default=0, ge=0)
    quizzes_completed_delta: int = Field(default=0, ge=0)
    quiz_score: float | None = Field(default=None, ge=0.0, le=100.0)
    study_minutes_delta: int = Field(default=0, ge=0)
    completion_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    mark_completed: bool = False
    mark_mastered: bool = False


class BookmarkRequest(BaseModel):
    pattern_session_id: UUID
    item_type: str = Field(..., min_length=1, max_length=50)
    item_id: str = Field(..., min_length=1, max_length=100)
    title: str | None = Field(default=None, max_length=500)


class BookmarkResponse(BaseModel):
    id: UUID
    pattern_session_id: UUID
    item_type: str
    item_id: str
    title: str | None = None
    created_at: datetime


class ExportRequest(BaseModel):
    pattern_session_id: UUID
    include: list[str] = Field(
        default_factory=lambda: [
            "overview",
            "mental_model",
            "recognition",
            "visualization",
            "templates",
            "examples",
            "interview_tips",
            "practice",
            "quiz",
            "comparison",
        ],
    )


class ExportResponse(BaseModel):
    pattern_session_id: UUID
    format: str
    filename: str
    content: str
    content_type: str


class PatternExampleResponse(BaseModel):
    id: str
    title: str
    pattern: str
    level: str
    language: str
    learning_style: str
    icon: str | None = None


class PatternAgentInfoResponse(BaseModel):
    role: str
    name: str
    description: str
    uses_openrouter: bool
    workflow_module: str | None = None
    prompt_module: str | None = None
    shared_path: str


class DeletePatternResponse(BaseModel):
    message: str = "Pattern session deleted successfully."
