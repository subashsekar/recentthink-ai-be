"""Maps between DSA Pattern Coach API schemas and shared AI platform schemas."""

from __future__ import annotations

from typing import Any

from app.agents.dsa_pattern.schemas import (
    ChatMessageResponse,
    CodeTemplate,
    FollowUpResponse,
    GeneratePatternRequest,
    GeneratePatternResponse,
    InterviewTips,
    MentalModel,
    NextPatternRecommendation,
    PatternComparisonItem,
    PatternContent,
    PatternHistoryItem,
    PatternOverview,
    PatternProgressSnapshot,
    PlannerOutput,
    PracticeContent,
    PracticeProblem,
    QuizContent,
    QuizQuestion,
    RecognitionGuide,
    SessionDetailResponse,
    TraceNode,
    UsageSummary,
    VisualizationContent,
    WalkthroughExample,
)
from app.models.ai_message import AIMessage
from app.models.dsa_pattern import PatternSession
from app.models.enums import AgentName, ModuleName, SessionStatus
from app.schemas.ai import ChatResponse, FollowUpResponse as PlatformFollowUpResponse
from app.schemas.ai import SessionDetailResponse as PlatformSessionDetailResponse


def build_chat_message(request: GeneratePatternRequest) -> str:
    return (
        f"Teach the DSA pattern end-to-end (recognition + mental model + templates + walkthroughs):\n"
        f"- pattern: {request.pattern}\n"
        f"- level: {request.level}\n"
        f"- preferred language: {request.language}\n"
        f"- learning_style: {request.learning_style}\n\n"
        f"REQUIRED completeness in dsa_pattern:\n"
        f"- overview (definition, history, why, use cases, beginner/intermediate/advanced)\n"
        f"- mental_model (analogies + intuition)\n"
        f"- recognition (keywords, signals, rules, decision tree, checklist)\n"
        f"- visualization (ASCII + step-by-step, frontend-friendly)\n"
        f"- templates for Python, Java, C++, JavaScript, Go, Rust, C# (reusable only)\n"
        f"- easy_example, medium_example, hard_example with full walkthroughs\n"
        f"- common_mistakes, interview_tips, pattern_comparison\n"
        f"- practice sets (easy/medium/hard/interview/contest/revision)\n"
        f"- quiz (mcqs, recognition, scenario, coding, flashcards, mini_assessment)\n"
        f"- next_pattern_recommendation\n"
        f"Focus on HOW TO THINK and HOW TO IDENTIFY the pattern. Return full JSON now."
    )


def build_pattern_context(request: GeneratePatternRequest) -> dict[str, Any]:
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


def _parse_practice(raw: dict[str, Any] | None) -> PracticeContent:
    payload = raw or {}
    try:
        return PracticeContent.model_validate(payload)
    except Exception:
        def _problems(key: str) -> list[PracticeProblem]:
            return [
                item
                for x in (payload.get(key) or [])
                if isinstance(x, dict)
                for item in [_safe_validate(PracticeProblem, x)]
                if item is not None
            ]

        return PracticeContent(
            roadmap=[str(x) for x in (payload.get("roadmap") or [])],
            easy=_problems("easy"),
            medium=_problems("medium"),
            hard=_problems("hard"),
            interview=_problems("interview"),
            contest=_problems("contest"),
            revision=_problems("revision"),
        )


def _parse_quiz(raw: dict[str, Any] | None) -> QuizContent:
    payload = raw or {}
    try:
        return QuizContent.model_validate(payload)
    except Exception:
        def _questions(key: str) -> list[QuizQuestion]:
            return [
                item
                for x in (payload.get(key) or [])
                if isinstance(x, dict)
                for item in [_safe_validate(QuizQuestion, x)]
                if item is not None
            ]

        return QuizContent(
            title=str(payload.get("title") or ""),
            mcqs=_questions("mcqs"),
            recognition_questions=_questions("recognition_questions"),
            scenario_questions=_questions("scenario_questions"),
            coding_questions=_questions("coding_questions"),
            flashcards=[x for x in (payload.get("flashcards") or []) if isinstance(x, dict)],
            mini_assessment=_questions("mini_assessment"),
        )


def _parse_walkthrough(raw: dict[str, Any] | None, *, difficulty: str) -> WalkthroughExample:
    payload = raw or {}
    try:
        example = WalkthroughExample.model_validate(payload)
        if not example.difficulty:
            example = example.model_copy(update={"difficulty": difficulty})
        return example
    except Exception:
        return WalkthroughExample(
            difficulty=difficulty,
            title=str(payload.get("title") or ""),
            problem_statement=str(payload.get("problem_statement") or ""),
            pattern_recognition=str(payload.get("pattern_recognition") or ""),
            approach=str(payload.get("approach") or ""),
            dry_run=[str(x) for x in (payload.get("dry_run") or [])],
            visualization=str(payload.get("visualization") or ""),
            code=str(payload.get("code") or ""),
            language=str(payload.get("language") or "python"),
            line_by_line=[str(x) for x in (payload.get("line_by_line") or [])],
            time_complexity=str(payload.get("time_complexity") or ""),
            space_complexity=str(payload.get("space_complexity") or ""),
            edge_cases=[str(x) for x in (payload.get("edge_cases") or [])],
            common_mistakes=[str(x) for x in (payload.get("common_mistakes") or [])],
        )


def _parse_pattern_content(raw: dict[str, Any] | None) -> PatternContent:
    payload = raw or {}
    try:
        return PatternContent.model_validate(payload)
    except Exception:
        overview_raw = payload.get("overview") if isinstance(payload.get("overview"), dict) else {}
        overview = _safe_validate(PatternOverview, overview_raw) or PatternOverview()
        mental = _safe_validate(MentalModel, payload.get("mental_model") or {}) or MentalModel()
        recognition = _safe_validate(RecognitionGuide, payload.get("recognition") or {}) or RecognitionGuide()
        visualization = (
            _safe_validate(VisualizationContent, payload.get("visualization") or {}) or VisualizationContent()
        )
        interview = _safe_validate(InterviewTips, payload.get("interview_tips") or {}) or InterviewTips()
        next_rec = (
            _safe_validate(NextPatternRecommendation, payload.get("next_pattern_recommendation") or {})
            or NextPatternRecommendation()
        )
        return PatternContent(
            overview=overview,
            mental_model=mental,
            recognition=recognition,
            visualization=visualization,
            templates=[
                item
                for x in (payload.get("templates") or [])
                if isinstance(x, dict)
                for item in [_safe_validate(CodeTemplate, x)]
                if item is not None
            ],
            easy_example=_parse_walkthrough(payload.get("easy_example"), difficulty="easy"),
            medium_example=_parse_walkthrough(payload.get("medium_example"), difficulty="medium"),
            hard_example=_parse_walkthrough(payload.get("hard_example"), difficulty="hard"),
            common_mistakes=[str(x) for x in (payload.get("common_mistakes") or [])],
            interview_tips=interview,
            pattern_comparison=[
                item
                for x in (payload.get("pattern_comparison") or [])
                if isinstance(x, dict)
                for item in [_safe_validate(PatternComparisonItem, x)]
                if item is not None
            ],
            practice=_parse_practice(payload.get("practice") if isinstance(payload.get("practice"), dict) else {}),
            quiz=_parse_quiz(payload.get("quiz") if isinstance(payload.get("quiz"), dict) else {}),
            next_pattern_recommendation=next_rec,
        )


def extract_pattern_from_chat(chat: ChatResponse) -> PatternContent:
    teacher = _module_structured(chat, ModuleName.TEACHER)
    raw = teacher.get("dsa_pattern") if isinstance(teacher.get("dsa_pattern"), dict) else {}
    if not raw:
        # Fallback if normalizer left it only on llm modules metadata.
        for item in chat.modules:
            structured = item.structured or {}
            if isinstance(structured.get("dsa_pattern"), dict):
                raw = structured["dsa_pattern"]
                break
    return _parse_pattern_content(raw)


def to_planner_output(chat: ChatResponse, request: GeneratePatternRequest) -> PlannerOutput:
    metadata = chat.planner.metadata or {}
    return PlannerOutput(
        pattern=str(metadata.get("pattern") or request.pattern),
        category=str(metadata.get("category") or "General"),
        difficulty=str(metadata.get("difficulty") or request.level),
        prerequisites=[str(x) for x in (metadata.get("prerequisites") or [])],
        estimated_study_time=str(metadata.get("estimated_study_time") or ""),
        learning_objectives=[str(x) for x in (metadata.get("learning_objectives") or [])],
        roadmap=[str(x) for x in (metadata.get("roadmap") or metadata.get("roadmap_outline") or [])],
        execution_plan=[str(x) for x in (metadata.get("execution_plan") or [])],
    )


def to_generate_response(
    chat: ChatResponse,
    request: GeneratePatternRequest,
    pattern_session: PatternSession,
    *,
    mode_id: str | None = None,
) -> GeneratePatternResponse:
    teacher_module = next((m for m in chat.modules if m.module == ModuleName.TEACHER), None)
    content = extract_pattern_from_chat(chat)
    overview = content.overview
    if not overview.pattern:
        overview = overview.model_copy(update={"pattern": request.pattern})

    return GeneratePatternResponse(
        session_id=chat.session_id,
        pattern_session_id=pattern_session.id,
        status=chat.status,
        mode_id=mode_id,
        request=request,
        planner=to_planner_output(chat, request),
        overview=overview,
        mental_model=content.mental_model,
        recognition=content.recognition,
        visualization=content.visualization,
        templates=content.templates,
        easy_example=content.easy_example,
        medium_example=content.medium_example,
        hard_example=content.hard_example,
        common_mistakes=content.common_mistakes,
        interview_tips=content.interview_tips,
        pattern_comparison=content.pattern_comparison,
        practice=content.practice,
        quiz=content.quiz,
        next_pattern_recommendation=content.next_pattern_recommendation,
        teacher_summary=teacher_module.content if teacher_module else "",
        progress=PatternProgressSnapshot(
            pattern_session_id=pattern_session.id,
            completion_pct=pattern_session.completion_pct,
            practice_completed=pattern_session.practice_completed,
            quiz_score=pattern_session.quiz_score,
            study_minutes=pattern_session.study_minutes,
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
            TraceNode(
                node="planner",
                status="SUCCESS" if chat.planner else "FAILED",
            ),
            TraceNode(
                node="openrouter",
                status="SUCCESS" if (chat.total_tokens or 0) > 0 or chat.model else "FAILED",
            ),
            TraceNode(
                node="learning_agent",
                status="SUCCESS" if content.overview.definition else "FAILED",
            ),
            TraceNode(
                node="recognition_agent",
                status="SUCCESS" if content.recognition.keywords or content.recognition.checklist else "FAILED",
            ),
            TraceNode(
                node="visualization_agent",
                status="SUCCESS"
                if content.visualization.ascii_diagrams or content.visualization.step_by_step
                else "FAILED",
            ),
            TraceNode(
                node="template_agent",
                status="SUCCESS" if content.templates else "FAILED",
            ),
            TraceNode(
                node="problem_walkthrough_agent",
                status="SUCCESS" if content.easy_example.title or content.medium_example.title else "FAILED",
            ),
            TraceNode(
                node="practice_agent",
                status="SUCCESS" if content.practice.easy or content.practice.roadmap else "FAILED",
            ),
            TraceNode(
                node="quiz_agent",
                status="SUCCESS" if content.quiz.mcqs or content.quiz.flashcards else "FAILED",
            ),
            TraceNode(node="progress_coach", status="SUCCESS"),
            TraceNode(node="persist", status="SUCCESS" if chat.status != SessionStatus.FAILED else "FAILED"),
        ],
    )


def pattern_to_content(row: PatternSession) -> PatternContent:
    if row.content and isinstance(row.content, dict):
        return _parse_pattern_content(row.content)
    return PatternContent(
        overview=PatternOverview.model_validate(row.overview or {}),
        mental_model=MentalModel.model_validate(row.mental_model or {}),
        recognition=RecognitionGuide.model_validate(row.recognition or {}),
        visualization=VisualizationContent.model_validate(row.visualization or {}),
        templates=[CodeTemplate.model_validate(x) for x in (row.templates or []) if isinstance(x, dict)],
        easy_example=_parse_walkthrough(row.easy_example, difficulty="easy"),
        medium_example=_parse_walkthrough(row.medium_example, difficulty="medium"),
        hard_example=_parse_walkthrough(row.hard_example, difficulty="hard"),
        common_mistakes=[str(x) for x in (row.common_mistakes or [])],
        interview_tips=InterviewTips.model_validate(row.interview_tips or {}),
        pattern_comparison=[
            PatternComparisonItem.model_validate(x) for x in (row.pattern_comparison or []) if isinstance(x, dict)
        ],
        practice=_parse_practice(row.practice if isinstance(row.practice, dict) else {}),
        quiz=_parse_quiz(row.quiz if isinstance(row.quiz, dict) else {}),
        next_pattern_recommendation=NextPatternRecommendation.model_validate(
            row.next_pattern_recommendation or {},
        ),
    )


def to_history_item(
    row: PatternSession,
    *,
    preview: str | None = None,
    message_count: int = 0,
    model_id: str | None = None,
) -> PatternHistoryItem:
    status = SessionStatus.COMPLETED
    if row.status == "active":
        status = SessionStatus.IN_PROGRESS
    snippet = preview
    if not snippet and row.description:
        snippet = row.description[:180]
    elif not snippet and isinstance(row.overview, dict):
        snippet = str(row.overview.get("definition") or row.overview.get("pattern") or "")[:180] or None
    return PatternHistoryItem(
        pattern_session_id=row.id,
        session_id=row.session_id,
        title=row.title,
        pattern=row.pattern_name,
        level=row.level,
        language=row.language,
        status=status,
        model_id=model_id,
        completion_pct=row.completion_pct,
        preview=snippet,
        message_count=message_count,
        created_at=row.created_at,
        updated_at=row.updated_at,
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
    pattern_session: PatternSession | None,
) -> SessionDetailResponse:
    return SessionDetailResponse(
        pattern_session_id=pattern_session.id if pattern_session else None,
        session_id=detail.session.id,
        title=detail.session.title or (pattern_session.title if pattern_session else None),
        pattern=pattern_session.pattern_name if pattern_session else None,
        level=pattern_session.level if pattern_session else None,
        language=pattern_session.language if pattern_session else None,
        status=detail.session.status,
        model_id=detail.session.model_id,
        mode_id=detail.session.mode_id,
        content=pattern_to_content(pattern_session) if pattern_session else None,
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


def content_to_markdown(content: PatternContent, *, include: list[str] | None = None) -> str:
    sections: list[str] = []
    wanted = set(
        include
        or [
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
    overview = content.overview
    sections.append(f"# {overview.pattern or 'DSA Pattern'}\n")
    if overview.definition:
        sections.append(overview.definition)
    if "overview" in wanted:
        if overview.beginner_explanation:
            sections.append("\n## Beginner Explanation\n")
            sections.append(overview.beginner_explanation)
        if overview.learning_objectives:
            sections.append("\n## Learning Objectives\n")
            sections.extend(f"- {item}" for item in overview.learning_objectives)
    if "mental_model" in wanted and content.mental_model.summary:
        sections.append("\n## Mental Model\n")
        sections.append(content.mental_model.summary)
        sections.extend(f"- {a}" for a in content.mental_model.analogies)
    if "recognition" in wanted:
        sections.append("\n## Recognition Guide\n")
        if content.recognition.how_to_identify:
            sections.append(content.recognition.how_to_identify)
        if content.recognition.keywords:
            sections.append("\nKeywords:")
            sections.extend(f"- {k}" for k in content.recognition.keywords)
        if content.recognition.checklist:
            sections.append("\nChecklist:")
            sections.extend(f"- {c}" for c in content.recognition.checklist)
    if "visualization" in wanted:
        sections.append("\n## Visualization\n")
        sections.extend(content.visualization.ascii_diagrams)
        sections.extend(f"- {s}" for s in content.visualization.step_by_step)
    if "templates" in wanted and content.templates:
        sections.append("\n## Templates\n")
        for tmpl in content.templates:
            sections.append(f"### {tmpl.language}\n")
            sections.append(f"```{tmpl.language}\n{tmpl.template}\n```")
    if "examples" in wanted:
        for label, example in (
            ("Easy", content.easy_example),
            ("Medium", content.medium_example),
            ("Hard", content.hard_example),
        ):
            if example.problem_statement or example.title:
                sections.append(f"\n## {label} Example: {example.title}\n")
                sections.append(example.problem_statement)
                if example.approach:
                    sections.append(f"\nApproach: {example.approach}")
                if example.code:
                    sections.append(f"\n```{example.language}\n{example.code}\n```")
    if "interview_tips" in wanted and content.interview_tips.interview_questions:
        sections.append("\n## Interview Tips\n")
        sections.extend(f"- {q}" for q in content.interview_tips.interview_questions)
    if "comparison" in wanted and content.pattern_comparison:
        sections.append("\n## Pattern Comparison\n")
        for item in content.pattern_comparison:
            sections.append(f"### vs {item.other_pattern}\n{item.summary}")
    if "practice" in wanted and content.practice.roadmap:
        sections.append("\n## Practice Roadmap\n")
        sections.extend(f"- {step}" for step in content.practice.roadmap)
    if "quiz" in wanted and content.quiz.mcqs:
        sections.append("\n## Quiz\n")
        for q in content.quiz.mcqs:
            sections.append(f"- ({q.type}) {q.question}")
    if content.next_pattern_recommendation.pattern:
        sections.append("\n## Next Pattern\n")
        sections.append(
            f"{content.next_pattern_recommendation.pattern}: {content.next_pattern_recommendation.reason}",
        )
    return "\n".join(sections)


def markdown_to_simple_pdf(markdown_text: str, title: str = "DSA Pattern") -> bytes:
    """Minimal single-page-stream PDF from plain text (no external deps)."""
    lines = markdown_text.replace("\r\n", "\n").split("\n")
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
