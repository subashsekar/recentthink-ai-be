"""Coaching mode registry (catalog + validation + fallback)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.coaching.schemas import ModeConfig, ModeMetadata
from shared.logging import get_logger

logger = get_logger(__name__)

DEFAULT_MODE_ID = "learning"

# services/ai_service/app/coaching/registry.py -> parents[1] == services/ai_service/app
_CATALOG_PATH = Path(__file__).resolve().parents[1] / "config" / "coaching_modes.json"


@lru_cache(maxsize=1)
def _load_catalog() -> dict:
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


class ModeRegistry:
    """Load and validate coaching modes from the JSON catalog."""

    def __init__(self, *, catalog_path: Path | None = None) -> None:
        self._catalog_path = catalog_path or _CATALOG_PATH
        self._modes = self._load_modes()

    def _load_modes(self) -> dict[str, ModeConfig]:
        try:
            raw = json.loads(self._catalog_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            logger.warning("Coaching mode catalog not found at %s", self._catalog_path)
            return {}
        except json.JSONDecodeError as exc:
            logger.error("Invalid coaching mode catalog JSON: %s", exc)
            return {}

        modes: dict[str, ModeConfig] = {}
        for item in raw.get("modes", []):
            if not isinstance(item, dict):
                continue
            cfg = ModeConfig.model_validate(item)
            modes[cfg.metadata.id] = cfg
        return modes

    def list_metadata(self) -> list[ModeMetadata]:
        """Return frontend-safe metadata for all modes."""
        return [cfg.metadata for cfg in self._modes.values()]

    def get(self, mode_id: str) -> ModeConfig | None:
        return self._modes.get(mode_id)

    def resolve(self, mode_id: str | None) -> ModeConfig:
        """Resolve a mode config with safe fallback to learning.

        Unknown mode IDs never crash the system.
        """
        resolved = (mode_id or DEFAULT_MODE_ID).strip() or DEFAULT_MODE_ID
        cfg = self.get(resolved)
        if cfg is not None:
            return cfg
        logger.warning("unknown_mode_id_fallback", extra={"mode_id": resolved})
        fallback = self.get(DEFAULT_MODE_ID)
        if fallback is not None:
            return fallback
        # Hard fallback if catalog missing: minimal learning mode.
        return ModeConfig(metadata=ModeMetadata(id=DEFAULT_MODE_ID, label="Learning Mode"))


@lru_cache(maxsize=1)
def get_mode_registry() -> ModeRegistry:
    return ModeRegistry()

