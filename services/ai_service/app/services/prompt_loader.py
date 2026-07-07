"""Load versioned prompts from the filesystem."""

from __future__ import annotations

from pathlib import Path

from app.core.config import AIServiceSettings, get_ai_settings
from app.repositories.prompt_version_repository import PromptVersionRepository
from shared.logging import get_logger

logger = get_logger(__name__)

PROMPTS_ROOT = Path(__file__).resolve().parents[1] / "prompts"


class PromptLoader:
    """Load prompts from files with versioning, hot reload, and DB overrides."""

    def __init__(
        self,
        *,
        prompts_root: Path | None = None,
        ai_settings: AIServiceSettings | None = None,
        prompt_repo: PromptVersionRepository | None = None,
    ) -> None:
        self._root = prompts_root or PROMPTS_ROOT
        self._settings = ai_settings or get_ai_settings()
        self._prompt_repo = prompt_repo
        self._cache: dict[tuple[str, str, str, str], str] = {}

    def clear_cache(self) -> None:
        self._cache.clear()

    def _cache_key(self, feature: str, module_name: str, version: str, locale: str) -> tuple[str, str, str, str]:
        return (feature, module_name, version, locale)

    def _resolve_path(
        self,
        feature: str,
        module_name: str,
        version: str,
        locale: str,
    ) -> Path:
        candidates = [
            self._root / feature / locale / version / f"{module_name}.md",
            self._root / feature / locale / version / f"{module_name}.txt",
            self._root / feature / version / f"{module_name}.md",
            self._root / feature / version / f"{module_name}.txt",
            self._root / "shared" / version / f"{module_name}.md",
            self._root / "shared" / version / f"{module_name}.txt",
            self._root / "shared" / f"{module_name}.md",
            self._root / "shared" / f"{module_name}.txt",
        ]
        for path in candidates:
            if path.is_file():
                return path
        return candidates[-1]

    def load(
        self,
        *,
        feature: str,
        module_name: str,
        version: str | None = None,
        locale: str | None = None,
    ) -> str:
        resolved_version = version or self._settings.prompt_default_version
        resolved_locale = locale or self._settings.prompt_default_locale
        key = self._cache_key(feature, module_name, resolved_version, resolved_locale)

        if not self._settings.prompt_hot_reload and key in self._cache:
            return self._cache[key]

        if self._prompt_repo is not None:
            db_prompt = self._prompt_repo.get_active(
                feature=feature,
                module_name=module_name,
                locale=resolved_locale,
            )
            if db_prompt is not None:
                content = db_prompt.content
                self._cache[key] = content
                return content

        path = self._resolve_path(feature, module_name, resolved_version, resolved_locale)
        if not path.is_file():
            msg = f"Prompt not found for feature={feature} module={module_name}"
            raise FileNotFoundError(msg)

        content = path.read_text(encoding="utf-8")
        self._cache[key] = content
        logger.debug("Loaded prompt from %s", path)
        return content
