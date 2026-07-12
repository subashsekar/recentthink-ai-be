"""Unit tests for DSA Pattern Coach adapter parsing and exports."""

from __future__ import annotations

from uuid import uuid4

from app.agents.dsa_pattern.adapter import (
    build_chat_message,
    build_pattern_context,
    content_to_markdown,
    extract_pattern_from_chat,
    to_planner_output,
)
from app.agents.dsa_pattern.schemas import (
    CodeTemplate,
    GeneratePatternRequest,
    PatternContent,
    PatternOverview,
    PracticeContent,
    QuizContent,
    QuizQuestion,
    RecognitionGuide,
    VisualizationContent,
)
from app.models.enums import AIFeature, ExecutionMode, ModuleName, SessionStatus
from app.schemas.ai import ChatResponse, ModuleResponse, PlannerOutput as PlatformPlannerOutput


def test_build_chat_message_includes_pattern() -> None:
    request = GeneratePatternRequest(pattern="Trie", level="Intermediate", language="Go", learning_style="Hands-on")
    message = build_chat_message(request)
    assert "Trie" in message
    assert "recognition" in message.lower()
    assert "Go" in message


def test_build_pattern_context() -> None:
    request = GeneratePatternRequest(pattern="Heap", level="Beginner", language="Python")
    ctx = build_pattern_context(request)
    assert ctx["pattern"] == "Heap"
    assert ctx["language"] == "Python"


def test_extract_pattern_recognition() -> None:
    chat = ChatResponse(
        session_id=uuid4(),
        status=SessionStatus.COMPLETED,
        planner=PlatformPlannerOutput(
            feature=AIFeature.DSA_PATTERN,
            modules=[ModuleName.TEACHER],
            execution_mode=ExecutionMode.SINGLE_LLM,
            metadata={"pattern": "Sliding Window", "category": "Sliding Window", "difficulty": "Beginner"},
        ),
        modules=[
            ModuleResponse(
                module=ModuleName.TEACHER,
                content="Sliding Window lesson",
                structured={
                    "dsa_pattern": {
                        "overview": {
                            "pattern": "Sliding Window",
                            "definition": "Contiguous window technique",
                            "learning_objectives": ["Identify window problems"],
                        },
                        "recognition": {
                            "keywords": ["substring", "subarray", "window"],
                            "signals": ["contiguous range"],
                            "recognition_rules": ["If contiguous, consider window"],
                            "checklist": ["Is the answer a contiguous segment?"],
                            "how_to_identify": "Look for contiguous constraints.",
                        },
                        "mental_model": {"summary": "Moving frame", "analogies": ["Telescope"]},
                        "visualization": {"ascii_diagrams": ["[L--R]"], "step_by_step": ["expand"]},
                        "templates": [
                            {
                                "language": "python",
                                "template": "left = 0\nfor right in range(n):\n    ...",
                                "description": "generic window",
                            },
                        ],
                        "easy_example": {
                            "difficulty": "easy",
                            "title": "Max Sum K",
                            "problem_statement": "Find max sum of size k",
                            "code": "def f(a,k): ...",
                        },
                        "medium_example": {"difficulty": "medium", "title": "Longest Unique"},
                        "hard_example": {"difficulty": "hard", "title": "Min Window"},
                        "common_mistakes": ["Never shrink"],
                        "interview_tips": {"interview_questions": ["When shrink?"]},
                        "pattern_comparison": [
                            {
                                "other_pattern": "Two Pointers",
                                "summary": "Window keeps size/state; two pointers may cross",
                            },
                        ],
                        "practice": {
                            "roadmap": ["Fixed then variable"],
                            "easy": [{"title": "Max Sum Subarray Size K", "difficulty": "easy"}],
                        },
                        "quiz": {
                            "title": "Quiz",
                            "mcqs": [
                                {
                                    "type": "mcq",
                                    "question": "Keyword for SW?",
                                    "options": ["subarray", "tree"],
                                    "answer": "subarray",
                                },
                            ],
                            "flashcards": [{"front": "SW?", "back": "Contiguous window"}],
                        },
                        "next_pattern_recommendation": {"pattern": "Two Pointers", "reason": "Related"},
                    },
                },
            ),
        ],
        input_tokens=10,
        output_tokens=20,
        total_tokens=30,
        latency_ms=5,
        execution_time_ms=5,
        estimated_cost=0.0,
        model="test",
    )
    content = extract_pattern_from_chat(chat)
    assert content.overview.pattern == "Sliding Window"
    assert "substring" in content.recognition.keywords
    assert content.templates[0].language == "python"
    assert content.quiz.mcqs[0].answer == "subarray"
    assert content.practice.easy[0].title.startswith("Max Sum")
    assert content.next_pattern_recommendation.pattern == "Two Pointers"


def test_to_planner_output_from_metadata() -> None:
    request = GeneratePatternRequest(pattern="Binary Search", level="Beginner", language="Java")
    chat = ChatResponse(
        session_id=uuid4(),
        status=SessionStatus.COMPLETED,
        planner=PlatformPlannerOutput(
            feature=AIFeature.DSA_PATTERN,
            modules=[ModuleName.TEACHER],
            execution_mode=ExecutionMode.SINGLE_LLM,
            metadata={
                "pattern": "Binary Search",
                "category": "Binary Search",
                "difficulty": "Beginner",
                "prerequisites": ["Sorted arrays"],
                "estimated_study_time": "4–6 hours",
                "learning_objectives": ["Search in log n"],
                "roadmap": ["Day 1"],
                "execution_plan": ["Plan"],
            },
        ),
        modules=[],
    )
    planner = to_planner_output(chat, request)
    assert planner.pattern == "Binary Search"
    assert planner.prerequisites == ["Sorted arrays"]


def test_visualization_template_quiz_practice_markdown() -> None:
    content = PatternContent(
        overview=PatternOverview(pattern="Stack", definition="LIFO structure"),
        recognition=RecognitionGuide(keywords=["next greater"], how_to_identify="Look for previous/next greater"),
        visualization=VisualizationContent(ascii_diagrams=["|a|b|c|"], step_by_step=["push", "pop"]),
        templates=[CodeTemplate(language="python", template="stack = []", description="generic stack")],
        quiz=QuizContent(
            title="Stack Quiz",
            mcqs=[
                QuizQuestion(
                    question="LIFO means?",
                    options=["Last in first out", "First in first out"],
                    answer="Last in first out",
                ),
            ],
        ),
        practice=PracticeContent(roadmap=["Learn push/pop"]),
    )
    md = content_to_markdown(content)
    assert "Stack" in md
    assert "Recognition" in md
    assert "Templates" in md
    assert "Quiz" in md


def test_pattern_content_defaults() -> None:
    content = PatternContent()
    assert content.overview.pattern == ""
    assert content.recognition.keywords == []
    assert content.templates == []
