"""Central registry for AI model catalog, allowlist, and validation."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import AIServiceSettings, get_ai_settings
from app.schemas.ai import ModelInfo, ModelsResponse
from shared.config import Settings, get_settings
from shared.exceptions.base import ValidationException
from shared.logging import get_logger

logger = get_logger(__name__)

_CATALOG_PATH = Path(__file__).resolve().parents[2] / "config" / "models.json"


class ModelCatalogEntry(BaseModel):
    """Static metadata for a model in the catalog."""

    id: str
    name: str
    provider: str
    description: str | None = None
    recommended: bool = False
    enabled: bool = True
    tier: str | None = None
    context_window: int | None = None
    supports_vision: bool = False
    supports_streaming: bool = True
    cost_per_1k_input: float | None = None
    cost_per_1k_output: float | None = None


class ModelRegistry:
    """Resolve, validate, and list models from catalog + deployment allowlist."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        ai_settings: AIServiceSettings | None = None,
        catalog_path: Path | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._ai_settings = ai_settings or get_ai_settings()
        self._catalog_path = catalog_path or _CATALOG_PATH
        self._catalog = self._load_catalog()

    def _load_catalog(self) -> dict[str, ModelCatalogEntry]:
        try:
            raw = json.loads(self._catalog_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            logger.warning("Model catalog not found at %s", self._catalog_path)
            return {}
        except json.JSONDecodeError as exc:
            logger.error("Invalid model catalog JSON: %s", exc)
            return {}

        entries: dict[str, ModelCatalogEntry] = {}
        for item in raw.get("models", []):
            if not isinstance(item, dict):
                continue
            entry = ModelCatalogEntry.model_validate(item)
            entries[entry.id] = entry
        return entries

    @property
    def default_model_id(self) -> str:
        return self._settings.openrouter_model

    def configured_model_ids(self) -> list[str]:
        return [
            item.strip()
            for item in self._ai_settings.available_models.split(",")
            if item.strip()
        ]

    def list_models(self, *, tier: str | None = None) -> ModelsResponse:
        """Return enabled models from the deployment allowlist with catalog metadata."""
        default_model = self.default_model_id
        models: list[ModelInfo] = []
        for model_id in self.configured_model_ids():
            entry = self._catalog.get(model_id)
            if entry is not None and not entry.enabled:
                continue
            if tier is not None and (entry is None or entry.tier != tier):
                continue
            models.append(self._to_model_info(model_id, entry, default_model=default_model))
        return ModelsResponse(models=models, default_model=default_model)

    def validate_model_id(self, model_id: str) -> None:
        """Reject unknown or disabled model IDs with HTTP 400."""
        if model_id not in self.configured_model_ids():
            raise ValidationException(
                f"Unknown model_id '{model_id}'. Use GET /ai/models for valid ids.",
            )
        entry = self._catalog.get(model_id)
        if entry is not None and not entry.enabled:
            raise ValidationException(f"Model '{model_id}' is not enabled.")

    def resolve_model_id(
        self,
        *,
        requested: str | None = None,
        session_model_id: str | None = None,
    ) -> str:
        """Pick model: explicit request → session → deployment default."""
        if requested is not None:
            self.validate_model_id(requested)
            return requested
        if session_model_id is not None:
            self.validate_model_id(session_model_id)
            return session_model_id
        default = self.default_model_id
        if default in self.configured_model_ids():
            entry = self._catalog.get(default)
            if entry is None or entry.enabled:
                return default
        enabled = self.list_models().models
        if not enabled:
            return default
        return enabled[0].id

    @staticmethod
    def _to_model_info(
        model_id: str,
        entry: ModelCatalogEntry | None,
        *,
        default_model: str,
    ) -> ModelInfo:
        if entry is None:
            provider = model_id.split("/", 1)[0] if "/" in model_id else "unknown"
            return ModelInfo(
                id=model_id,
                name=model_id,
                provider=provider.title(),
                description=None,
                recommended=False,
                default=model_id == default_model,
                enabled=True,
            )
        return ModelInfo(
            id=entry.id,
            name=entry.name,
            provider=entry.provider,
            description=entry.description,
            recommended=entry.recommended,
            default=entry.id == default_model,
            enabled=entry.enabled,
            tier=entry.tier,
            context_window=entry.context_window,
            supports_vision=entry.supports_vision,
            supports_streaming=entry.supports_streaming,
            cost_per_1k_input=entry.cost_per_1k_input,
            cost_per_1k_output=entry.cost_per_1k_output,
        )


@lru_cache(maxsize=1)
def get_model_registry() -> ModelRegistry:
    """Return a process-wide model registry."""
    return ModelRegistry()
