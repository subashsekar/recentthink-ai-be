"""Streaming handler for LLM responses."""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.clients.openrouter import OpenRouterClient


class StreamingHandler:
    """Thin wrapper around OpenRouter streaming for future SSE endpoints."""

    def __init__(self, llm_client: OpenRouterClient | None = None) -> None:
        self._llm = llm_client or OpenRouterClient()

    async def stream(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        async for chunk in self._llm.stream_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield chunk
