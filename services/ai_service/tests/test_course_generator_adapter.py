"""Unit tests for Course Generator adapter, planner metadata, and export helpers."""

from __future__ import annotations

from uuid import uuid4

from app.agents.course_generator.adapter import (
    build_chat_message,
    build_course_context,
    content_to_markdown,
    extract_course_from_chat,
    markdown_to_simple_pdf,
    to_planner_output,
)
from app.agents.course_generator.schemas import (
    CourseContent,
    CourseOverview,
    GenerateCourseRequest,
    LessonContent,
    WeekRoadmap,
)
from app.agents.shared.llm_response_normalizer import is_llm_response_empty, normalize_unified_llm_payload
from app.agents.shared.planner.planner import Planner
from app.models.enums import AIFeature, ExecutionMode, ModuleName, SessionStatus
from app.schemas.ai import ChatRequest, ChatResponse, ModuleResponse, PlannerOutput as PlatformPlanner
from app.schemas.llm_response import UnifiedLLMResponse


def test_build_chat_message_and_context() -> None:
    request = GenerateCourseRequest(skill="Python", goal="Become AI Engineer")
    message = build_chat_message(request)
    context = build_course_context(request)
    assert "Python" in message
    assert "COMPLETE" in message
    assert "lessons" in message.lower()
    assert context["skill"] == "Python"
    assert context["goal"] == "Become AI Engineer"


def test_planner_course_generator_metadata() -> None:
    planner = Planner()
    output = planner.plan(
        ChatRequest(
            feature=AIFeature.COURSE_GENERATOR,
            message="Generate learning path",
            context={
                "skill": "Python",
                "goal": "Become AI Engineer",
                "level": "Beginner",
                "duration_days": 60,
                "daily_hours": 2,
                "learning_style": "Hands-on",
                "programming_language": "Python",
                "topics_include": ["ML", "NLP"],
            },
        ),
    )
    assert output.feature == AIFeature.COURSE_GENERATOR
    assert output.modules == [ModuleName.TEACHER]
    assert output.execution_mode == ExecutionMode.SINGLE_LLM
    assert output.metadata["skill"] == "Python"
    assert output.metadata["estimated_study_hours"] == 120.0
    assert output.metadata["learning_objectives"]
    assert output.metadata["roadmap_outline"]
    assert output.metadata["milestones"]


def test_unified_llm_response_accepts_course() -> None:
    payload = UnifiedLLMResponse.model_validate(
        {
            "teacher": {"problem_summary": "A course", "explanation": "Intro"},
            "course": {
                "overview": {"title": "Python Path", "description": "Learn Python"},
                "roadmap": [{"week": 1, "title": "Basics"}],
                "lessons": [],
                "quizzes": [],
                "assignments": [],
                "projects": [],
                "assessments": [],
                "resources": [],
                "learning_tips": ["Practice daily"],
                "next_recommendations": ["Deep Learning"],
                "adaptive": {"struggling": ["Extra practice"], "excelling": ["Skip basics"]},
            },
        },
    )
    assert payload.course
    normalized = normalize_unified_llm_payload(payload.model_dump())
    assert not is_llm_response_empty(normalized)
    assert normalized["course"]["overview"]["title"] == "Python Path"


def test_extract_course_from_chat() -> None:
    chat = ChatResponse(
        session_id=uuid4(),
        status=SessionStatus.COMPLETED,
        planner=PlatformPlanner(
            feature=AIFeature.COURSE_GENERATOR,
            modules=[ModuleName.TEACHER],
            execution_mode=ExecutionMode.SINGLE_LLM,
            metadata={"skill": "Python", "goal": "AI", "duration_days": 30, "daily_hours": 1},
        ),
        modules=[
            ModuleResponse(
                module=ModuleName.TEACHER,
                content="Course intro",
                structured={
                    "problem_summary": "Intro",
                    "course": {
                        "overview": {"title": "Python 30-Day Path", "description": "Fast track"},
                        "roadmap": [{"week": 1, "title": "Foundations", "daily_topics": []}],
                        "lessons": [
                            {
                                "title": "Variables",
                                "concept_explanation": "Names for values",
                                "objectives": ["Declare variables"],
                            },
                        ],
                        "quizzes": [],
                        "assignments": [],
                        "projects": [],
                        "assessments": [],
                        "resources": [],
                        "learning_tips": ["Code daily"],
                        "next_recommendations": [],
                        "adaptive": {},
                    },
                },
            ),
        ],
        total_tokens=10,
    )
    content = extract_course_from_chat(chat)
    assert content.overview.title == "Python 30-Day Path"
    assert content.lessons[0].title == "Variables"
    planner = to_planner_output(
        chat,
        GenerateCourseRequest(skill="Python", goal="AI", duration_days=30, daily_hours=1),
    )
    assert planner.skill == "Python"
    assert planner.estimated_study_hours == 30.0


def test_content_to_markdown_and_pdf() -> None:
    content = CourseContent.model_validate(
        {
            "overview": {"title": "Test Course", "description": "Desc", "learning_objectives": ["Obj1"]},
            "roadmap": [{"week": 1, "title": "Week 1", "focus": "Basics"}],
            "lessons": [{"title": "L1", "concept_explanation": "Explain", "summary": "Sum"}],
            "assignments": [
                {
                    "week": 1,
                    "title": "Week 1 Lab",
                    "type": "weekly",
                    "description": "Practice setup and first scripts.",
                    "tasks": ["Create project folder", "Write hello.py"],
                    "coding_exercises": ["Write add(a,b) returning a+b. Example: add(2,3)->5"],
                    "review_questions": ["What is a virtual environment?"],
                    "estimated_hours": 3,
                }
            ],
            "projects": [
                {
                    "title": "Calculator",
                    "level": "beginner",
                    "description": "CLI calculator",
                    "requirements": ["Support + - * /"],
                    "implementation_steps": ["Parse input", "Compute result"],
                    "expected_output": "Working CLI",
                    "evaluation_criteria": ["Handles divide by zero"],
                }
            ],
            "assessments": [
                {
                    "week": 1,
                    "title": "Week 1 Check",
                    "type": "weekly",
                    "questions": ["Explain variables"],
                    "rubric": ["Accuracy"],
                    "scoring": "10 points",
                    "completion_criteria": ["Score >= 7"],
                }
            ],
            "learning_tips": ["Tip"],
        }
    )
    md = content_to_markdown(content)
    assert "# Test Course" in md
    assert "Week 1" in md
    assert "**Coding exercises**" in md
    assert "Write add(a,b)" in md
    assert "**Review questions**" in md
    assert "**Evaluation criteria**" in md
    assert "**Rubric**" in md
    pdf = markdown_to_simple_pdf(md, title="Test Course")
    assert pdf.startswith(b"%PDF")
    assert b"%%EOF" in pdf


def test_course_empty_detection() -> None:
    assert is_llm_response_empty({"teacher": {}, "coder": {}, "course": {}})
    assert not is_llm_response_empty(
        {"teacher": {}, "coder": {}, "course": {"overview": {"title": "X"}}},
    )


def test_lesson_id_coerces_int_to_str() -> None:
    from app.agents.course_generator.adapter import _parse_course_content

    content = _parse_course_content(
        {
            "overview": {"title": "Path"},
            "lessons": [{"id": 1, "title": "Intro", "objectives": ["Learn"]}],
            "quizzes": [{"id": 2, "title": "Q1", "questions": [{"answer": True, "question": "T/F?"}]}],
            "projects": [{"id": 3, "title": "P1"}],
        },
    )
    assert content.lessons[0].id == "1"
    assert content.quizzes[0].id == "2"
    assert content.quizzes[0].questions[0].answer == "True"
    assert content.projects[0].id == "3"

