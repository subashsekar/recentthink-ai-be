"""Mode prompt loader.

Mode prompts are dedicated templates (not a tiny prefix). The workflow composes:
- mode prompt template (personality + strategy)
- schema/output requirements prompt (shared single-LLM JSON contract)
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from shared.logging import get_logger

logger = get_logger(__name__)

PROMPTS_ROOT = Path(__file__).resolve().parent / "prompts"


class ModePromptLoader:
    """Load mode-specific prompts from app/coaching/prompts/."""

    def __init__(self, *, prompts_root: Path | None = None) -> None:
        self._root = prompts_root or PROMPTS_ROOT

    def load(self, prompt_id: str) -> str:
        # prompt_id examples: "learning", "teacher", "interview", "quick"
        path = self._root / f"{prompt_id}.txt"
        if not path.is_file():
            logger.warning("mode_prompt_not_found", extra={"prompt_id": prompt_id, "path": str(path)})
            return ""
        return path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def get_mode_prompt_loader() -> ModePromptLoader:
    return ModePromptLoader()

