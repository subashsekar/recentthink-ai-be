"""Maps between Course Generator API schemas and shared AI platform schemas."""

from __future__ import annotations

from typing import Any

from app.agents.course_generator.schemas import (
    AdaptiveRecommendations,
    AssessmentContent,
    AssignmentContent,
    ChatMessageResponse,
    CourseChatHistoryDetailResponse,
    CourseContent,
    CourseHistoryItem,
    CourseOverview,
    CourseProgressSnapshot,
    FollowUpResponse,
    GenerateCourseRequest,
    GenerateCourseResponse,
    LessonContent,
    PlannerOutput,
    ProjectContent,
    QuizContent,
    ResourceItem,
    SessionDetailResponse,
    TraceNode,
    UsageSummary,
    WeekRoadmap,
)
from app.models.ai_message import AIMessage
from app.models.course import Course
from app.models.enums import AgentName, ModuleName
from app.schemas.ai import ChatResponse, FollowUpResponse as PlatformFollowUpResponse
from app.schemas.ai import SessionDetailResponse as PlatformSessionDetailResponse


def build_chat_message(request: GenerateCourseRequest) -> str:
    weeks = max(4, request.duration_days // 7)
    min_lessons = weeks * 2
    return (
        f"Generate a COMPLETE personalized course (not just a roadmap) for:\n"
        f"- skill: {request.skill}\n"
        f"- goal: {request.goal}\n"
        f"- current level: {request.level}\n"
        f"- target level: {request.target_level or 'Advanced'}\n"
        f"- duration_days: {request.duration_days} (~{weeks} weeks)\n"
        f"- daily_hours: {request.daily_hours}\n"
        f"- learning_style: {request.learning_style}\n"
        f"- instruction language: {request.language}\n"
        f"- programming_language: {request.programming_language}\n"
        f"- topics_include: {request.topics_include or []}\n"
        f"- topics_exclude: {request.topics_exclude or []}\n"
        f"- output_format: {request.output_format}\n\n"
        f"REQUIRED completeness:\n"
        f"- roadmap for all {weeks} weeks with daily topics\n"
        f"- at least {min_lessons} full lessons with concept_explanation, examples, analogies\n"
        f"- at least {weeks} quizzes (5+ questions each) with flashcards\n"
        f"- at least {weeks} assignments with tasks and coding exercises\n"
        f"- 4 projects (beginner, intermediate, advanced, resume)\n"
        f"- weekly assessments + one final assessment\n"
        f"- 8+ resources, learning tips, adaptive recommendations\n"
        f"Return the full course JSON now."
    )


def build_course_context(request: GenerateCourseRequest) -> dict[str, Any]:
    return request.model_dump()


def _module_structured(chat: ChatResponse, module: ModuleName) -> dict[str, Any]:
    for item in chat.modules:
        if item.module == module:
            return item.structured or {}
    return {}


def _safe_validate(model: type, item: dict[str, Any]) -> Any | None:
    try:
        return model.model_validate(item)
    except Exception:
        return None


def _parse_course_content(raw: dict[str, Any] | None) -> CourseContent:
    payload = raw or {}
    try:
        return CourseContent.model_validate(payload)
    except Exception:
        overview_raw = payload.get("overview") if isinstance(payload.get("overview"), dict) else {}
        overview = _safe_validate(CourseOverview, overview_raw) or CourseOverview()
        adaptive_raw = payload.get("adaptive") if isinstance(payload.get("adaptive"), dict) else {}
        adaptive = _safe_validate(AdaptiveRecommendations, adaptive_raw) or AdaptiveRecommendations()
        return CourseContent(
            overview=overview,
            roadmap=[
                item
                for w in (payload.get("roadmap") or [])
                if isinstance(w, dict)
                for item in [_safe_validate(WeekRoadmap, w)]
                if item is not None
            ],
            lessons=[
                item
                for x in (payload.get("lessons") or [])
                if isinstance(x, dict)
                for item in [_safe_validate(LessonContent, x)]
                if item is not None
            ],
            quizzes=[
                item
                for x in (payload.get("quizzes") or [])
                if isinstance(x, dict)
                for item in [_safe_validate(QuizContent, x)]
                if item is not None
            ],
            assignments=[
                item
                for x in (payload.get("assignments") or [])
                if isinstance(x, dict)
                for item in [_safe_validate(AssignmentContent, x)]
                if item is not None
            ],
            projects=[
                item
                for x in (payload.get("projects") or [])
                if isinstance(x, dict)
                for item in [_safe_validate(ProjectContent, x)]
                if item is not None
            ],
            assessments=[
                item
                for x in (payload.get("assessments") or [])
                if isinstance(x, dict)
                for item in [_safe_validate(AssessmentContent, x)]
                if item is not None
            ],
            resources=[
                item
                for x in (payload.get("resources") or [])
                if isinstance(x, dict)
                for item in [_safe_validate(ResourceItem, x)]
                if item is not None
            ],
            learning_tips=[str(x) for x in (payload.get("learning_tips") or [])],
            next_recommendations=[str(x) for x in (payload.get("next_recommendations") or [])],
            adaptive=adaptive,
        )


def extract_course_from_chat(chat: ChatResponse) -> CourseContent:
    teacher = _module_structured(chat, ModuleName.TEACHER)
    raw_course = teacher.get("course") if isinstance(teacher.get("course"), dict) else {}
    return _parse_course_content(raw_course)


def to_planner_output(chat: ChatResponse, request: GenerateCourseRequest) -> PlannerOutput:
    metadata = chat.planner.metadata or {}
    duration = int(metadata.get("duration_days") or request.duration_days)
    daily = float(metadata.get("daily_hours") or request.daily_hours)
    return PlannerOutput(
        skill=str(metadata.get("skill") or request.skill),
        goal=str(metadata.get("goal") or request.goal),
        difficulty=str(metadata.get("difficulty") or request.level),
        duration_days=duration,
        daily_hours=daily,
        estimated_study_hours=float(metadata.get("estimated_study_hours") or round(duration * daily, 1)),
        learning_objectives=[str(x) for x in (metadata.get("learning_objectives") or [])],
        prerequisites=[str(x) for x in (metadata.get("prerequisites") or [])],
        roadmap_outline=[str(x) for x in (metadata.get("roadmap_outline") or [])],
        milestones=[str(x) for x in (metadata.get("milestones") or [])],
        execution_plan=[str(x) for x in (metadata.get("execution_plan") or [])],
    )


def to_generate_response(
    chat: ChatResponse,
    request: GenerateCourseRequest,
    course: Course,
    *,
    mode_id: str | None = None,
) -> GenerateCourseResponse:
    teacher_module = next((m for m in chat.modules if m.module == ModuleName.TEACHER), None)
    content = extract_course_from_chat(chat)
    overview = content.overview
    if not overview.title:
        overview = overview.model_copy(update={"title": course.title})

    return GenerateCourseResponse(
        session_id=chat.session_id,
        course_id=course.id,
        status=chat.status,
        mode_id=mode_id,
        request=request,
        planner=to_planner_output(chat, request),
        overview=overview,
        roadmap=content.roadmap,
        lessons=content.lessons,
        quizzes=content.quizzes,
        assignments=content.assignments,
        projects=content.projects,
        assessments=content.assessments,
        resources=content.resources,
        learning_tips=content.learning_tips,
        next_recommendations=content.next_recommendations,
        adaptive=content.adaptive,
        teacher_summary=teacher_module.content if teacher_module else "",
        progress=CourseProgressSnapshot(
            course_id=course.id,
            current_week=course.current_week,
            current_lesson=course.current_lesson,
            completion_pct=course.completion_pct,
            lessons_completed=course.lessons_completed,
            quizzes_completed=course.quizzes_completed,
            projects_completed=course.projects_completed,
            study_hours=course.study_hours,
        ),
        usage=UsageSummary(
            input_tokens=chat.input_tokens,
            output_tokens=chat.output_tokens,
            total_tokens=chat.total_tokens,
            latency_ms=chat.latency_ms,
            execution_time_ms=chat.execution_time_ms,
            estimated_cost=chat.estimated_cost,
            model=chat.model,
        ),
        execution_trace=[
            TraceNode(node="planner"),
            TraceNode(node="openrouter"),
            TraceNode(node="course_generator"),
            TraceNode(node="roadmap_generator"),
            TraceNode(node="lesson_generator"),
            TraceNode(node="quiz_generator"),
            TraceNode(node="assignment_generator"),
            TraceNode(node="project_generator"),
            TraceNode(node="assessment_generator"),
            TraceNode(node="persist"),
        ],
    )


def course_to_content(course: Course) -> CourseContent:
    if course.content and isinstance(course.content, dict):
        return _parse_course_content(course.content)
    return CourseContent(
        overview=CourseOverview.model_validate(course.overview or {}),
        roadmap=[WeekRoadmap.model_validate(w) for w in (course.roadmap or []) if isinstance(w, dict)],
        lessons=[LessonContent.model_validate(x) for x in (course.lessons or []) if isinstance(x, dict)],
        quizzes=[QuizContent.model_validate(x) for x in (course.quizzes or []) if isinstance(x, dict)],
        assignments=[
            AssignmentContent.model_validate(x) for x in (course.assignments or []) if isinstance(x, dict)
        ],
        projects=[ProjectContent.model_validate(x) for x in (course.projects or []) if isinstance(x, dict)],
        assessments=[
            AssessmentContent.model_validate(x) for x in (course.assessments or []) if isinstance(x, dict)
        ],
        resources=[ResourceItem.model_validate(x) for x in (course.resources or []) if isinstance(x, dict)],
        learning_tips=[str(x) for x in (course.learning_tips or [])],
        next_recommendations=[str(x) for x in (course.next_recommendations or [])],
        adaptive=AdaptiveRecommendations.model_validate(course.adaptive or {}),
    )


def to_history_item(
    course: Course,
    *,
    preview: str | None = None,
    message_count: int = 0,
    model_id: str | None = None,
) -> CourseHistoryItem:
    from app.models.enums import SessionStatus

    status = SessionStatus.COMPLETED if course.status == "completed" else SessionStatus.COMPLETED
    if course.status == "active":
        status = SessionStatus.IN_PROGRESS
    snippet = preview
    if not snippet and course.description:
        snippet = course.description[:180]
    elif not snippet and isinstance(course.overview, dict):
        snippet = str(course.overview.get("description") or course.overview.get("title") or "")[:180] or None
    return CourseHistoryItem(
        course_id=course.id,
        session_id=course.session_id,
        title=course.title,
        skill=course.skill,
        goal=course.goal,
        level=course.level,
        status=status,
        model_id=model_id,
        completion_pct=course.completion_pct,
        preview=snippet,
        message_count=message_count,
        created_at=course.created_at,
        updated_at=course.updated_at,
    )


def to_chat_history_detail(
    detail: PlatformSessionDetailResponse,
    course: Course,
) -> CourseChatHistoryDetailResponse:
    messages = [_to_chat_message(message) for message in detail.messages]
    return CourseChatHistoryDetailResponse(
        course_id=course.id,
        session_id=detail.session.id,
        title=detail.session.title or course.title,
        skill=course.skill,
        goal=course.goal,
        level=course.level,
        status=detail.session.status,
        model_id=detail.session.model_id,
        mode_id=detail.session.mode_id,
        messages=messages,
        total_messages=len(messages),
        content=course_to_content(course),
        created_at=detail.session.created_at,
        updated_at=detail.session.updated_at,
    )


def _to_agent_name(module_name: ModuleName | None) -> AgentName | None:
    if module_name is None:
        return None
    mapping = {
        ModuleName.PLANNER: AgentName.PLANNER,
        ModuleName.TEACHER: AgentName.TEACHER,
        ModuleName.CODER: AgentName.CODER,
        ModuleName.EVALUATOR: AgentName.EVALUATOR,
    }
    return mapping.get(module_name)


def _to_chat_message(message: AIMessage) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        role=message.role,
        agent_name=_to_agent_name(message.module_name),
        message=message.content,
        created_at=message.created_at,
    )


def to_session_detail(
    detail: PlatformSessionDetailResponse,
    course: Course | None,
) -> SessionDetailResponse:
    return SessionDetailResponse(
        course_id=course.id if course else None,
        session_id=detail.session.id,
        title=detail.session.title or (course.title if course else None),
        skill=course.skill if course else None,
        goal=course.goal if course else None,
        level=course.level if course else None,
        status=detail.session.status,
        model_id=detail.session.model_id,
        mode_id=detail.session.mode_id,
        content=course_to_content(course) if course else None,
        messages=[_to_chat_message(message) for message in detail.messages],
        created_at=detail.session.created_at,
        updated_at=detail.session.updated_at,
    )


def to_follow_up_response(response: PlatformFollowUpResponse) -> FollowUpResponse:
    return FollowUpResponse(
        session_id=response.session_id,
        intent=response.intent,
        teacher=response.teacher.content,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        total_tokens=response.total_tokens,
        latency_ms=response.latency_ms,
        execution_time_ms=response.execution_time_ms,
    )


def content_to_markdown(content: CourseContent, *, include: list[str] | None = None) -> str:
    sections: list[str] = []
    wanted = set(include or ["roadmap", "lessons", "projects", "assignments", "quiz", "assessment", "resources"])
    overview = content.overview
    sections.append(f"# {overview.title or 'Learning Path'}\n")
    if overview.description:
        sections.append(overview.description)
    if overview.learning_objectives:
        sections.append("\n## Learning Objectives\n")
        sections.extend(f"- {item}" for item in overview.learning_objectives)
    if "roadmap" in wanted and content.roadmap:
        sections.append("\n## Roadmap\n")
        for week in content.roadmap:
            sections.append(f"### Week {week.week}: {week.title}\n")
            if week.focus:
                sections.append(week.focus)
            for topic in week.daily_topics:
                sections.append(f"- Day {topic.day}: {topic.topic}")
    if "lessons" in wanted and content.lessons:
        sections.append("\n## Lessons\n")
        for lesson in content.lessons:
            sections.append(f"### {lesson.title}\n")
            if lesson.concept_explanation:
                sections.append(lesson.concept_explanation)
            if lesson.summary:
                sections.append(f"\n**Summary:** {lesson.summary}")
    if "assignments" in wanted and content.assignments:
        sections.append("\n## Assignments\n")
        for item in content.assignments:
            sections.append(f"### {item.title}\n{item.description}")
            sections.extend(f"- {task}" for task in item.tasks)
    if "projects" in wanted and content.projects:
        sections.append("\n## Projects\n")
        for project in content.projects:
            sections.append(f"### {project.title} ({project.level})\n")
            sections.append(project.description)
            if project.implementation_steps:
                sections.append("\nSteps:")
                sections.extend(f"{i}. {step}" for i, step in enumerate(project.implementation_steps, 1))
    if "quiz" in wanted and content.quizzes:
        sections.append("\n## Quizzes\n")
        for quiz in content.quizzes:
            sections.append(f"### {quiz.title}\n")
            for q in quiz.questions:
                sections.append(f"- ({q.type}) {q.question}")
    if "assessment" in wanted and content.assessments:
        sections.append("\n## Assessments\n")
        for assessment in content.assessments:
            sections.append(f"### {assessment.title}\n")
            sections.extend(f"- {q}" for q in assessment.questions)
    if "resources" in wanted and content.resources:
        sections.append("\n## Resources\n")
        for resource in content.resources:
            link = f" ({resource.url})" if resource.url else ""
            sections.append(f"- {resource.title}{link}: {resource.description}")
    if content.learning_tips:
        sections.append("\n## Learning Tips\n")
        sections.extend(f"- {tip}" for tip in content.learning_tips)
    return "\n".join(sections)


def markdown_to_simple_pdf(markdown_text: str, title: str = "Learning Path") -> bytes:
    """Minimal single-page-stream PDF from plain text (no external deps)."""
    lines = markdown_text.replace("\r\n", "\n").split("\n")
    # Escape PDF special chars and limit line width.
    safe_lines: list[str] = []
    for line in lines:
        cleaned = (
            line.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
            .replace("#", "")
            .strip()
        )
        if len(cleaned) > 90:
            while cleaned:
                safe_lines.append(cleaned[:90])
                cleaned = cleaned[90:]
        else:
            safe_lines.append(cleaned)
    safe_lines = safe_lines[:200] or [title]

    content_lines = ["BT", "/F1 10 Tf", "50 780 Td", "14 TL"]
    for index, line in enumerate(safe_lines):
        if index == 0:
            content_lines.append(f"({line}) Tj")
        else:
            content_lines.append("T*")
            content_lines.append(f"({line}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="replace")

    objects: list[bytes] = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objects.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n",
    )
    objects.append(f"4 0 obj<< /Length {len(stream)} >>stream\n".encode() + stream + b"\nendstream\nendobj\n")
    objects.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(
        f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode(),
    )
    return bytes(pdf)
