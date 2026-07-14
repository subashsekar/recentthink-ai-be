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
