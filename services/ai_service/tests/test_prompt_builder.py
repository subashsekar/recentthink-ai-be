"""PromptBuilder unit tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from app.core.config import AIServiceSettings
from app.models.enums import AIFeature, ExecutionMode, ModuleName
from app.prompts.builder import PromptBuilder
from app.schemas.ai import PlannerOutput
from app.services.prompt_loader import PromptLoader


def _write_prompt_tree(root: Path) -> None:
    shared = root / "shared"
    shared.mkdir(parents=True)
    (shared / "system.md").write_text("SYSTEM", encoding="utf-8")
    (shared / "safety.md").write_text("SAFETY", encoding="utf-8")
    (shared / "output_schema.md").write_text("SCHEMA", encoding="utf-8")
    features = root / "features"
    features.mkdir(parents=True)
    (features / "leetcode.md").write_text("LEETCODE_MASTER", encoding="utf-8")
    (features / "hackerrank.md").write_text("HACKERRANK_MASTER", encoding="utf-8")
    (features / "course_generator.md").write_text("COURSE_MASTER", encoding="utf-8")


def test_prompt_loader_resolves_feature_master(tmp_path: Path) -> None:
    _write_prompt_tree(tmp_path)
    loader = PromptLoader(
        prompts_root=tmp_path,
        ai_settings=AIServiceSettings(prompt_hot_reload=True),
    )
    assert loader.load_feature_master("leetcode") == "LEETCODE_MASTER"
    assert loader.load(feature="hackerrank", module_name="single_llm") == "HACKERRANK_MASTER"
    assert loader.load_shared("system") == "SYSTEM"


def test_prompt_builder_composes_shared_and_feature(tmp_path: Path) -> None:
    _write_prompt_tree(tmp_path)
    loader = PromptLoader(
        prompts_root=tmp_path,
        ai_settings=AIServiceSettings(prompt_hot_reload=True),
    )
    mode_loader = MagicMock()
    mode_loader.load.return_value = "MODE"
    builder = PromptBuilder(prompt_loader=loader, mode_prompt_loader=mode_loader)
    planner = PlannerOutput(
        feature=AIFeature.LEETCODE,
        modules=[ModuleName.TEACHER, ModuleName.CODER],
        execution_mode=ExecutionMode.SINGLE_LLM,
        metadata={"difficulty": "Easy", "patterns": ["Hash Map"]},
    )
    built = builder.build(
        planner=planner,
        message="Explain Two Sum",
        context={"title": "Two Sum"},
        mode_id="learning",
    )
    assert "SYSTEM" in built.system_prompt
    assert "SAFETY" in built.system_prompt
    assert "SCHEMA" in built.system_prompt
    assert "MODE" in built.system_prompt
    assert "LEETCODE_MASTER" in built.system_prompt
    assert "Two Sum" in built.user_prompt
    assert "Explain Two Sum" in built.user_prompt


def test_prompt_builder_skips_mode_for_course(tmp_path: Path) -> None:
    _write_prompt_tree(tmp_path)
    loader = PromptLoader(
        prompts_root=tmp_path,
        ai_settings=AIServiceSettings(prompt_hot_reload=True),
    )
    mode_loader = MagicMock()
    mode_loader.load.return_value = "MODE"
    builder = PromptBuilder(prompt_loader=loader, mode_prompt_loader=mode_loader)
    planner = PlannerOutput(
        feature=AIFeature.COURSE_GENERATOR,
        modules=[ModuleName.TEACHER],
        execution_mode=ExecutionMode.SINGLE_LLM,
        metadata={"skill": "Python", "weeks": 4, "duration_days": 28},
    )
    built = builder.build(planner=planner, message="Build a Python path", mode_id="learning")
    assert "COURSE_MASTER" in built.system_prompt
    assert "MODE" not in built.system_prompt
    mode_loader.load.assert_not_called()


def test_prompt_builder_analyze_paths_for_coverage(tmp_path: Path) -> None:
    _write_prompt_tree(tmp_path)
    (tmp_path / "features" / "dsa_pattern.md").write_text("DSA_MASTER", encoding="utf-8")
    (tmp_path / "features" / "interview.md").write_text("INTERVIEW_MASTER", encoding="utf-8")
    loader = PromptLoader(
        prompts_root=tmp_path,
        ai_settings=AIServiceSettings(prompt_hot_reload=True),
    )
    mode_loader = MagicMock()
    mode_loader.load.return_value = "MODE"
    builder = PromptBuilder(prompt_loader=loader, mode_prompt_loader=mode_loader)

    hr_planner = PlannerOutput(
        feature=AIFeature.HACKERRANK,
        modules=[ModuleName.TEACHER],
        execution_mode=ExecutionMode.SINGLE_LLM,
        metadata={"difficulty": "Medium", "domain": "SQL", "patterns": ["Aggregation"]},
    )
    hr = builder.build(
        planner=hr_planner,
        message="Analyze challenge",
        context={"title": "Weather", "difficulty": "Medium"},
        memory_context={"summary": "prior", "extra": {"k": 1}},
        mode_id="learning",
        requested_sections=["teacher"],
    )
    assert "Challenge metadata" in hr.user_prompt
    assert "INCREMENTAL GENERATION" in hr.system_prompt

    dsa_planner = PlannerOutput(
        feature=AIFeature.DSA_PATTERN,
        modules=[ModuleName.TEACHER],
        execution_mode=ExecutionMode.SINGLE_LLM,
        metadata={"pattern": "Two Pointers", "difficulty": "Easy", "language": "Python"},
    )
    dsa = builder.build(planner=dsa_planner, message="Teach pattern", mode_id="learning")
    assert "DSA pattern request metadata" in dsa.user_prompt

    interview_planner = PlannerOutput(
        feature=AIFeature.INTERVIEW,
        modules=[ModuleName.TEACHER],
        execution_mode=ExecutionMode.SINGLE_LLM,
        metadata={"interview_type": "system_design", "role_target": "SDE", "focus_areas": ["APIs"]},
    )
    interview = builder.build(
        planner=interview_planner,
        message="Mock interview",
        context={"role": "Backend"},
        mode_id="learning",
    )
    assert "Interview request metadata" in interview.user_prompt


def test_prompt_builder_followup_hackerrank_and_pattern_and_course(tmp_path: Path) -> None:
    _write_prompt_tree(tmp_path)
    loader = PromptLoader(
        prompts_root=tmp_path,
        ai_settings=AIServiceSettings(prompt_hot_reload=True),
    )
    builder = PromptBuilder(prompt_loader=loader, mode_prompt_loader=MagicMock())

    hr = builder.build_followup(
        feature=AIFeature.HACKERRANK,
        question="Optimize this algorithm.",
        intent="optimize",
        instructions="Optimize",
        session_context={"title": "Sorting", "domain": "Algorithms", "description": "sort fast"},
        memory_context={"teacher_output": {"approach": "sort"}, "planner_output": {"modules": ["teacher"]}},
        session_outputs={"coder": {"complexity": {"time": "O(n log n)"}}},
        followup_module_prompt="FOLLOWUP",
    )
    assert "Challenge:" in hr.user_prompt
    assert "Coder:" in hr.user_prompt

    dsa = builder.build_followup(
        feature=AIFeature.DSA_PATTERN,
        question="Explain Sliding Window again.",
        intent="explain_again",
        instructions="Re-explain",
        session_context={"pattern": "Sliding Window", "level": "Beginner"},
        memory_context={},
        session_outputs={"dsa_pattern": {"overview": "window", "quiz": []}},
        followup_module_prompt="FOLLOWUP",
    )
    assert "Pattern: Sliding Window" in dsa.user_prompt
    assert "Pattern outputs:" in dsa.user_prompt

    course = builder.build_followup(
        feature=AIFeature.COURSE_GENERATOR,
        question="Expand Lesson 5.",
        intent="generate_practice",
        instructions="Expand",
        session_context={"skill": "Python", "goal": "Backend APIs", "duration_days": 30},
        memory_context={},
        session_outputs={"course": {"roadmap": [1, 2], "lessons": [1, 2, 3], "assignments": [1]}},
        followup_module_prompt="FOLLOWUP",
        requested_sections=["teacher"],
    )
    assert "Skill: Python" in course.user_prompt
    assert "Course outputs:" in course.user_prompt
    assert "Requested sections" in course.user_prompt


def test_prompt_builder_followup_uses_summaries_not_full_dumps(tmp_path: Path) -> None:
    _write_prompt_tree(tmp_path)
    loader = PromptLoader(
        prompts_root=tmp_path,
        ai_settings=AIServiceSettings(prompt_hot_reload=True),
    )
    builder = PromptBuilder(prompt_loader=loader, mode_prompt_loader=MagicMock())
    huge_teacher = {
        "problem_summary": "Two Sum",
        "approach": "Hash map",
        "concepts": ["Hash Map"],
        "explanation": "x" * 5000,
        "unused_giant_block": "y" * 8000,
    }
    built = builder.build_followup(
        feature=AIFeature.LEETCODE,
        question="Explain why HashMap works.",
        intent="general",
        instructions="Stay in mentor mode.",
        session_context={"title": "Two Sum", "description": "Find pair summing to target", "difficulty": "Easy"},
        memory_context={
            "summary": "Prior discussion",
            "teacher_output": huge_teacher,
            "recent_messages": [
                {"role": "user", "content": "Analyze"},
                {"role": "assistant", "content": "Here is the approach"},
                {"role": "user", "content": "old-1"},
                {"role": "assistant", "content": "old-2"},
                {"role": "user", "content": "old-3"},
                {"role": "assistant", "content": "old-4"},
                {"role": "user", "content": "old-5"},
                {"role": "assistant", "content": "old-6"},
                {"role": "user", "content": "latest-user"},
                {"role": "assistant", "content": "latest-assistant"},
            ],
        },
        session_outputs={"coder": {"complexity": {"time": "O(n)", "space": "O(n)"}}},
        mode_prompt="MODE_FOLLOWUP",
        teacher_system="TEACHER_SYSTEM",
        followup_module_prompt="FOLLOWUP_MODULE",
    )
    assert "MODE_FOLLOWUP" in built.system_prompt
    assert "Two Sum" in built.user_prompt
    assert "Explain why HashMap works." in built.user_prompt
    assert "Current AI outputs" in built.user_prompt
    assert "unused_giant_block" not in built.user_prompt
    assert "yyyyyyyy" not in built.user_prompt
    assert "latest-user" in built.user_prompt
    # Only latest conversation window is included.
    assert built.user_prompt.count("old-1") == 0

