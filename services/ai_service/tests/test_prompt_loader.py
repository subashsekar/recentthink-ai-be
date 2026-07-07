"""Prompt loader unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.core.config import AIServiceSettings
from app.services.prompt_loader import PromptLoader


@pytest.fixture
def prompts_root(tmp_path: Path) -> Path:
    shared_dir = tmp_path / "shared" / "v1"
    shared_dir.mkdir(parents=True)
    (shared_dir / "single_llm.txt").write_text("Shared prompt", encoding="utf-8")

    feature_dir = tmp_path / "leetcode" / "v1"
    feature_dir.mkdir(parents=True)
    (feature_dir / "single_llm.txt").write_text("LeetCode prompt", encoding="utf-8")
    return tmp_path


def test_load_feature_prompt(prompts_root: Path) -> None:
    loader = PromptLoader(
        prompts_root=prompts_root,
        ai_settings=AIServiceSettings(prompt_hot_reload=True),
    )
    content = loader.load(feature="leetcode", module_name="single_llm")
    assert content == "LeetCode prompt"


def test_load_shared_fallback(prompts_root: Path) -> None:
    loader = PromptLoader(
        prompts_root=prompts_root,
        ai_settings=AIServiceSettings(prompt_hot_reload=True),
    )
    content = loader.load(feature="hackerrank", module_name="single_llm")
    assert content == "Shared prompt"


def test_cache_when_hot_reload_disabled(prompts_root: Path) -> None:
    loader = PromptLoader(
        prompts_root=prompts_root,
        ai_settings=AIServiceSettings(prompt_hot_reload=False),
    )
    first = loader.load(feature="leetcode", module_name="single_llm")
    path = prompts_root / "leetcode" / "v1" / "single_llm.txt"
    path.write_text("Updated", encoding="utf-8")
    second = loader.load(feature="leetcode", module_name="single_llm")
    assert first == second == "LeetCode prompt"


def test_missing_prompt_raises(prompts_root: Path) -> None:
    loader = PromptLoader(prompts_root=prompts_root)
    with pytest.raises(FileNotFoundError):
        loader.load(feature="leetcode", module_name="missing")


def test_load_md_prompt(prompts_root: Path) -> None:
    teacher_dir = prompts_root / "teacher" / "v1"
    teacher_dir.mkdir(parents=True)
    (teacher_dir / "system.md").write_text("Teacher system prompt", encoding="utf-8")
    loader = PromptLoader(
        prompts_root=prompts_root,
        ai_settings=AIServiceSettings(prompt_hot_reload=True),
    )
    content = loader.load(feature="teacher", module_name="system")
    assert content == "Teacher system prompt"
