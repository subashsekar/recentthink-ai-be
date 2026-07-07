"""Conversation summarizer — generates long-term memory summaries."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from app.clients.openrouter import OpenRouterClient
from app.services.prompt_loader import PromptLoader
from shared.logging import get_logger

logger = get_logger(__name__)


class ConversationSummarizer:
    """Generate conversation summaries for token optimization."""

    def __init__(
        self,
        *,
        llm_client: OpenRouterClient | None = None,
        prompt_loader: PromptLoader | None = None,
    ) -> None:
        self._llm = llm_client or OpenRouterClient()
        self._prompts = prompt_loader or PromptLoader()

    async def summarize(
        self,
        *,
        session_id: UUID,
        messages: list[dict[str, Any]],
        existing_summary: str | None = None,
        model: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        system_prompt = self._prompts.load(feature="teacher", module_name="summary")
        user_sections = []
        if existing_summary:
            user_sections.append(f"Existing summary:\n{existing_summary}")
        user_sections.append(f"Conversation:\n{json.dumps(messages, indent=2)}")
        user_prompt = "\n\n".join(user_sections)

        response = await self._llm.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=0.2,
            max_tokens=1024,
        )

        summary = response.content.strip()
        usage = {
            "input_tokens": response.prompt_tokens,
            "output_tokens": response.completion_tokens,
            "total_tokens": response.total_tokens,
            "model": response.model,
            "latency_ms": response.latency_ms,
        }
        logger.info(
            "summary_created",
            extra={"session_id": str(session_id), "tokens": usage["total_tokens"]},
        )
        return summary, usage
