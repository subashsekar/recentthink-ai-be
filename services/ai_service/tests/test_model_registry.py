"""Model registry unit tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.models.model_registry import ModelRegistry
from shared.exceptions.base import ValidationException


@pytest.fixture
def registry(tmp_path: Path) -> ModelRegistry:
    catalog = {
        "models": [
            {
                "id": "google/gemini-2.5-flash",
                "name": "Gemini 2.5 Flash",
                "provider": "Google",
                "description": "Fast",
                "recommended": True,
                "enabled": True,
            },
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "provider": "OpenAI",
                "description": "Premium",
                "recommended": False,
                "enabled": True,
            },
            {
                "id": "disabled/model",
                "name": "Disabled",
                "provider": "Test",
                "enabled": False,
            },
        ],
    }
    catalog_path = tmp_path / "models.json"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

    from unittest.mock import MagicMock

    settings = MagicMock()
    settings.openrouter_model = "google/gemini-2.5-flash"
    ai_settings = MagicMock()
    ai_settings.available_models = (
        "google/gemini-2.5-flash,openai/gpt-4o,disabled/model,unknown/model"
    )
    return ModelRegistry(settings=settings, ai_settings=ai_settings, catalog_path=catalog_path)


def test_list_models_returns_catalog_metadata(registry: ModelRegistry) -> None:
    result = registry.list_models()
    assert result.default_model == "google/gemini-2.5-flash"
    assert len(result.models) == 3
    gemini = result.models[0]
    assert gemini.id == "google/gemini-2.5-flash"
    assert gemini.name == "Gemini 2.5 Flash"
    assert gemini.provider == "Google"
    assert gemini.recommended is True
    assert gemini.default is True
    assert gemini.enabled is True


def test_list_models_omits_disabled_catalog_entries(registry: ModelRegistry) -> None:
    ids = [model.id for model in registry.list_models().models]
    assert "disabled/model" not in ids


def test_list_models_includes_unknown_allowlist_with_minimal_metadata(
    registry: ModelRegistry,
) -> None:
    unknown = next(m for m in registry.list_models().models if m.id == "unknown/model")
    assert unknown.name == "unknown/model"
    assert unknown.enabled is True


def test_validate_model_id_rejects_unknown(registry: ModelRegistry) -> None:
    with pytest.raises(ValidationException, match="Unknown model_id"):
        registry.validate_model_id("not-real/model")


def test_validate_model_id_rejects_disabled(registry: ModelRegistry) -> None:
    with pytest.raises(ValidationException, match="not enabled"):
        registry.validate_model_id("disabled/model")


def test_resolve_model_id_prefers_request(registry: ModelRegistry) -> None:
    assert (
        registry.resolve_model_id(
            requested="openai/gpt-4o",
            session_model_id="google/gemini-2.5-flash",
        )
        == "openai/gpt-4o"
    )


def test_resolve_model_id_uses_session_when_request_missing(registry: ModelRegistry) -> None:
    assert (
        registry.resolve_model_id(
            requested=None,
            session_model_id="openai/gpt-4o",
        )
        == "openai/gpt-4o"
    )


def test_resolve_model_id_falls_back_to_default(registry: ModelRegistry) -> None:
    assert registry.resolve_model_id(requested=None, session_model_id=None) == (
        "google/gemini-2.5-flash"
    )
