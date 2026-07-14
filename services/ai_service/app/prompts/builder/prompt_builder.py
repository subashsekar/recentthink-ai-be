"""Compose one master system prompt and one user prompt per AI product request."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.coaching.prompt_loader import ModePromptLoader, get_mode_prompt_loader
from app.coaching.registry import get_mode_registry
from app.models.enums import AIFeature
from app.schemas.ai import PlannerOutput
from app.services.prompt_loader import PromptLoader


@dataclass(frozen=True)
class BuiltPrompt:
    """Final prompts for a single OpenRouter call."""

    system_prompt: str
    user_prompt: str
    feature: str
    mode_id: str | None
    prompt_modules: tuple[str, ...]


# Features that must not inherit LeetCode-style coaching mode overlays.
_NO_MODE_OVERLAY: frozenset[str] = frozenset(
    {
        AIFeature.COURSE_GENERATOR.value,
        AIFeature.DSA_PATTERN.value,
    },
)


class PromptBuilder:
    """Load shared + feature prompts and build ONE final prompt pair.

    Workflow nodes must call this builder instead of composing prompts inline.
    """

    def __init__(
        self,
        *,
        prompt_loader: PromptLoader | None = None,
        mode_prompt_loader: ModePromptLoader | None = None,
    ) -> None:
        self._prompts = prompt_loader or PromptLoader()
        self._mode_prompts = mode_prompt_loader or get_mode_prompt_loader()

    def build(
        self,
        *,
        planner: PlannerOutput,
        message: str,
        context: dict[str, Any] | None = None,
        memory_context: dict[str, Any] | None = None,
        title: str | None = None,
        mode_id: str | None = None,
        requested_sections: list[str] | None = None,
    ) -> BuiltPrompt:
        feature = planner.feature.value
        mode_registry = get_mode_registry()
        mode_cfg = mode_registry.resolve(mode_id)
        mode_prompt_id = mode_cfg.analyze_prompt or mode_cfg.metadata.id

        system_prompt = self._build_system_prompt(
            feature=feature,
            mode_prompt_id=mode_prompt_id,
            requested_sections=requested_sections,
        )
        user_prompt = self._build_user_prompt(
            planner=planner,
            message=message,
            context=context,
            memory_context=memory_context,
            title=title,
            requested_sections=requested_sections,
        )
        return BuiltPrompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            feature=feature,
            mode_id=mode_cfg.metadata.id,
            prompt_modules=("system", "safety", "output_schema", "master"),
        )

    def _build_system_prompt(
        self,
        *,
        feature: str,
        mode_prompt_id: str,
        requested_sections: list[str] | None = None,
    ) -> str:
        # Use PromptLoader.load() so tests can mock a single load() method.
        parts: list[str] = [
            self._prompts.load(feature="shared", module_name="system"),
            self._prompts.load(feature="shared", module_name="safety"),
            self._prompts.load(feature="shared", module_name="output_schema"),
        ]

        if feature not in _NO_MODE_OVERLAY:
            mode_prompt = self._mode_prompts.load(mode_prompt_id)
            if isinstance(mode_prompt, str) and mode_prompt.strip():
                parts.append(mode_prompt.strip())

        parts.append(self._prompts.load(feature=feature, module_name="master"))
        if requested_sections:
            named = ", ".join(requested_sections)
            parts.append(
                "INCREMENTAL GENERATION RULES:\n"
                f"- Generate ONLY these sections: {named}.\n"
                "- Do NOT regenerate or expand any other sections.\n"
                "- Omitted sections must be null/absent — the client will reuse prior values.\n"
                "- Still return valid unified JSON with the same schema shape."
            )
        return "\n\n".join(str(part) for part in parts if part and str(part).strip())

    def _build_user_prompt(
        self,
        *,
        planner: PlannerOutput,
        message: str,
        context: dict[str, Any] | None,
        memory_context: dict[str, Any] | None,
        title: str | None,
        requested_sections: list[str] | None = None,
    ) -> str:
        sections = [
            f"Feature: {planner.feature.value}",
            f"Classification: {planner.metadata.get('classification', 'general')}",
            f"Modules: {', '.join(module.value for module in planner.modules)}",
        ]
        metadata = planner.metadata or {}
        feature = planner.feature.value

        if feature == AIFeature.LEETCODE.value:
            sections.append(self._leetcode_metadata(metadata, context, title))
        elif feature == AIFeature.HACKERRANK.value:
            sections.append(self._hackerrank_metadata(metadata, context, title))
        elif feature == AIFeature.COURSE_GENERATOR.value:
            sections.append(self._course_metadata(metadata))
        elif feature == AIFeature.DSA_PATTERN.value:
            sections.append(self._dsa_pattern_metadata(metadata))
        elif feature == AIFeature.INTERVIEW.value:
            sections.append(self._interview_metadata(metadata, context))

        if requested_sections:
            sections.append(
                "Requested sections (generate ONLY these):\n"
                + json.dumps({"sections": requested_sections}, indent=2)
            )

        if context:
            # Avoid duplicating large prior payloads into the prompt twice.
            ctx_for_prompt = {
                key: value
                for key, value in context.items()
                if key not in {"prior_llm_raw", "existing_response", "existing_sections"}
            }
            if ctx_for_prompt:
                sections.append(f"Context:\n{json.dumps(ctx_for_prompt, indent=2, default=str)}")
        if memory_context:
            sections.extend(self._memory_sections(memory_context))
        sections.append(f"User request:\n{message}")
        return "\n\n".join(sections)

    @staticmethod
    def _leetcode_metadata(
        metadata: dict[str, Any],
        context: dict[str, Any] | None,
        title: str | None,
    ) -> str:
        ctx = context or {}
        resolved_title = title or ctx.get("title") or metadata.get("problem_slug") or "Unknown"
        lines = [
            f"Title: {resolved_title}",
            f"Difficulty: {metadata.get('difficulty') or ctx.get('difficulty') or 'Unknown'}",
            f"Category: {metadata.get('problem_category', 'General')}",
            f"Patterns: {', '.join(metadata.get('patterns') or ctx.get('topics') or [])}",
        ]
        PromptBuilder._append_objectives_and_plan(lines, metadata)
        return "Problem metadata:\n" + "\n".join(lines)

    @staticmethod
    def _hackerrank_metadata(
        metadata: dict[str, Any],
        context: dict[str, Any] | None,
        title: str | None,
    ) -> str:
        ctx = context or {}
        resolved_title = title or ctx.get("title") or metadata.get("challenge_slug") or "Unknown"
        lines = [
            f"Title: {resolved_title}",
            f"Difficulty: {metadata.get('difficulty') or ctx.get('difficulty') or 'Unknown'}",
            f"Domain: {metadata.get('domain') or ctx.get('domain') or 'General'}",
            f"Patterns: {', '.join(metadata.get('patterns') or ctx.get('topics') or [])}",
        ]
        PromptBuilder._append_objectives_and_plan(lines, metadata)
        return "Challenge metadata:\n" + "\n".join(lines)

    @staticmethod
    def _course_metadata(metadata: dict[str, Any]) -> str:
        weeks = int(metadata.get("weeks") or max(4, int(metadata.get("duration_days") or 60) // 7))
        min_lessons = weeks * 2
        lines = [
            f"Skill: {metadata.get('skill', 'General')}",
            f"Goal: {metadata.get('goal', '')}",
            f"Level: {metadata.get('current_level') or metadata.get('difficulty', 'Beginner')}",
            f"Target level: {metadata.get('target_level', 'Advanced')}",
            f"Duration: {metadata.get('duration_days', 60)} days @ {metadata.get('daily_hours', 2)}h/day",
            f"Estimated study hours: {metadata.get('estimated_study_hours', 0)}",
            f"Learning style: {metadata.get('learning_style', 'Hands-on')}",
            f"Instruction language: {metadata.get('language', 'English')}",
            f"Programming language: {metadata.get('programming_language', 'Python')}",
            "",
            "COMPLETENESS REQUIREMENTS (do not skip):",
            f"- roadmap for all {weeks} weeks with daily_topics",
            f"- >= {min_lessons} full lessons (concept_explanation + examples + analogies)",
            f"- >= {weeks} quizzes with 5+ questions and flashcards each",
            f"- >= {weeks} assignments with tasks + coding_exercises",
            "- 4 projects: beginner, intermediate, advanced, resume",
            "- weekly assessments + one final assessment",
            "- 8+ resources, learning_tips, adaptive recommendations",
            "- Populate feature (course payload) fully — roadmap/lessons/quizzes/assignments/projects/assessments",
        ]
        if metadata.get("topics_include"):
            lines.append(f"Include topics: {', '.join(metadata['topics_include'])}")
        if metadata.get("topics_exclude"):
            lines.append(f"Exclude topics: {', '.join(metadata['topics_exclude'])}")
        PromptBuilder._append_objectives_and_plan(lines, metadata)
        return "Course request metadata:\n" + "\n".join(lines)

    @staticmethod
    def _dsa_pattern_metadata(metadata: dict[str, Any]) -> str:
        lines = [
            f"Pattern: {metadata.get('pattern', 'General')}",
            f"Category: {metadata.get('category', 'General')}",
            f"Level / difficulty: {metadata.get('difficulty') or metadata.get('level', 'Beginner')}",
            f"Preferred language: {metadata.get('language', 'Python')}",
            f"Learning style: {metadata.get('learning_style', 'Visual')}",
            f"Estimated study time: {metadata.get('estimated_study_time', '')}",
            "",
            "COMPLETENESS REQUIREMENTS (do not skip):",
            "- overview with beginner/intermediate/advanced explanations",
            "- mental_model with analogies",
            "- recognition keywords/signals/rules/decision_tree/checklist",
            "- visualization (ASCII + step-by-step, frontend-friendly)",
            "- reusable templates for Python, Java, C++, JavaScript, Go, Rust, C#",
            "- easy_example, medium_example, hard_example with full walkthroughs",
            "- interview_tips, pattern_comparison, practice sets, quiz",
            "- next_pattern_recommendation",
            "- Populate feature fully — focus on HOW TO IDENTIFY the pattern",
        ]
        PromptBuilder._append_objectives_and_plan(lines, metadata)
        return "DSA pattern request metadata:\n" + "\n".join(lines)

    @staticmethod
    def _interview_metadata(metadata: dict[str, Any], context: dict[str, Any] | None) -> str:
        ctx = context or {}
        lines = [
            f"Interview type: {metadata.get('interview_type') or ctx.get('interview_type') or 'technical'}",
            f"Role target: {metadata.get('role_target') or ctx.get('role') or 'Software Engineer'}",
            f"Seniority: {metadata.get('seniority') or ctx.get('seniority') or 'mid'}",
            f"Focus areas: {', '.join(metadata.get('focus_areas') or ctx.get('focus_areas') or [])}",
        ]
        PromptBuilder._append_objectives_and_plan(lines, metadata)
        return "Interview request metadata:\n" + "\n".join(lines)

    @staticmethod
    def _append_objectives_and_plan(lines: list[str], metadata: dict[str, Any]) -> None:
        objectives = metadata.get("learning_objectives") or []
        if objectives:
            lines.append("Learning objectives:")
            lines.extend(f"- {item}" for item in objectives)
        plan = metadata.get("execution_plan") or []
        if plan:
            lines.append("Execution plan:")
            lines.extend(f"{index}. {step}" for index, step in enumerate(plan, start=1))

    @staticmethod
    def _memory_sections(memory_context: dict[str, Any]) -> list[str]:
        sections: list[str] = []
        if memory_context.get("summary"):
            sections.append(f"Conversation summary:\n{memory_context['summary']}")
        if memory_context.get("planner_output"):
            sections.append(
                f"Prior planner output:\n{json.dumps(memory_context['planner_output'], indent=2, default=str)}",
            )
        if memory_context.get("teacher_output"):
            sections.append(
                f"Prior teacher output:\n{json.dumps(memory_context['teacher_output'], indent=2, default=str)}",
            )
        if memory_context.get("recent_messages"):
            sections.append(
                f"Recent messages:\n{json.dumps(memory_context['recent_messages'], indent=2, default=str)}",
            )
        remaining = {
            key: value
            for key, value in memory_context.items()
            if key not in {"summary", "planner_output", "teacher_output", "recent_messages", "context"}
        }
        if remaining:
            sections.append(f"Memory:\n{json.dumps(remaining, indent=2, default=str)}")
        return sections
