"""Context pruning for token optimization."""

from __future__ import annotations

import json
from typing import Any

DEFAULT_MAX_RECENT_MESSAGES = 10
DEFAULT_MAX_SUMMARY_CHARS = 2000
DEFAULT_MAX_CONTEXT_CHARS = 4000


class ContextPruner:
    """Prune conversation context to reduce token usage."""

    def __init__(
        self,
        *,
        max_recent_messages: int = DEFAULT_MAX_RECENT_MESSAGES,
        max_summary_chars: int = DEFAULT_MAX_SUMMARY_CHARS,
        max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
    ) -> None:
        self._max_recent = max_recent_messages
        self._max_summary = max_summary_chars
        self._max_context = max_context_chars

    def prune_recent_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return messages[-self._max_recent :]

    def prune_summary(self, summary: str | None) -> str | None:
        if not summary:
            return None
        if len(summary) <= self._max_summary:
            return summary
        return summary[: self._max_summary - 3] + "..."

    def prune_context(self, context: dict[str, Any] | None) -> dict[str, Any]:
        if not context:
            return {}
        serialized = json.dumps(context, default=str)
        if len(serialized) <= self._max_context:
            return context
        pruned: dict[str, Any] = {}
        for key in ("problem", "planner_output", "teacher_output", "feature"):
            if key in context:
                pruned[key] = context[key]
        return pruned or {"truncated": True}

    def should_summarize(self, *, message_count: int, recent_messages: list) -> bool:
        return message_count > self._max_recent or len(recent_messages) > self._max_recent

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)
