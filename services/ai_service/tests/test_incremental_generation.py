"""Incremental generation + section token apportionment tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from app.core.config import AIServiceSettings
from app.models.enums import AIFeature, ExecutionMode, ModuleName
from app.prompts.builder import PromptBuilder
from app.schemas.ai import PlannerOutput
from app.services.prompt_loader import PromptLoader
from app.utils.section_tokens import (
    estimate_section_tokens,
    filter_payload_to_sections,
    merge_llm_payload,
    resolve_prior_payload,
)


def _write_prompt_tree(root: Path) -> None:
    shared = root / "shared"
    shared.mkdir(parents=True)
    (shared / "system.md").write_text("SYSTEM", encoding="utf-8")
    (shared / "safety.md").write_text("SAFETY", encoding="utf-8")
    (shared / "output_schema.md").write_text("SCHEMA", encoding="utf-8")
    features = root / "features"
    features.mkdir(parents=True)
    (features / "leetcode.md").write_text("LEETCODE_MASTER", encoding="utf-8")


def test_prompt_builder_includes_requested_sections(tmp_path: Path) -> None:
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
        metadata={},
    )
    built = builder.build(
        planner=planner,
        message="Explain",
        requested_sections=["teacher", "practice"],
    )
    assert "INCREMENTAL GENERATION" in built.system_prompt
    assert "teacher" in built.user_prompt
    assert "practice" in built.user_prompt
    assert '"sections"' in built.user_prompt


def test_merge_reuses_unchanged_sections() -> None:
    prior = {
        "teacher": {"content": "old-teacher"},
        "coder": {"code": "old-code"},
        "feature": {"practice": "old-practice", "quiz": "old-quiz"},
    }
    generated = {
        "teacher": {"content": "new-teacher"},
        "feature": {"practice": "new-practice"},
    }
    merged = merge_llm_payload(prior, generated, requested_sections=["teacher", "practice"])
    assert merged["teacher"]["content"] == "new-teacher"
    assert merged["coder"]["code"] == "old-code"
    assert merged["feature"]["practice"] == "new-practice"
    assert merged["feature"]["quiz"] == "old-quiz"


def test_filter_payload_to_sections() -> None:
    payload = {
        "teacher": {"a": 1},
        "coder": {"b": 2},
        "feature": {"practice": 3, "quiz": 4},
    }
    filtered = filter_payload_to_sections(payload, ["teacher", "practice"])
    assert "teacher" in filtered
    assert "coder" not in filtered
    assert filtered["feature"] == {"practice": 3}


def test_estimate_section_tokens_sums_to_completion() -> None:
    payload = {
        "teacher": {"x": "a" * 100},
        "coder": {"y": "b" * 50},
        "feature": {"practice": {"z": "c" * 25}},
    }
    tokens = estimate_section_tokens(payload, completion_tokens=100)
    assert sum(tokens.values()) == 100
    assert tokens["teacher"] >= tokens["coder"]


def test_estimate_with_requested_sections_only() -> None:
    payload = {
        "teacher": {"x": "a" * 100},
        "coder": {"y": "b" * 100},
    }
    tokens = estimate_section_tokens(
        payload,
        completion_tokens=40,
        requested_sections=["teacher"],
    )
    assert set(tokens.keys()) == {"teacher"}
    assert tokens["teacher"] == 40


def test_resolve_prior_payload_from_context() -> None:
    prior = resolve_prior_payload(
        context={"prior_llm_raw": {"teacher": {"ok": True}}},
        memory_context=None,
    )
    assert prior == {"teacher": {"ok": True}}


def test_full_generation_replaces_payload() -> None:
    prior = {"teacher": {"old": True}}
    generated = {"teacher": {"new": True}, "coder": {"c": 1}}
    assert merge_llm_payload(prior, generated, requested_sections=None) == generated
