"""Conversation summarizer unit tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.agents.shared.memory.summarizer import ConversationSummarizer
from app.clients.openrouter import LLMResponse


@pytest.mark.asyncio
async def test_summarizer_returns_summary() -> None:
    llm = AsyncMock()
    llm.chat_completion.return_value = LLMResponse(
        content="The learner discussed two sum using a hash map.",
        model="openai/gpt-4o-mini",
        provider="openai",
        prompt_tokens=50,
        completion_tokens=30,
        latency_ms=100,
        estimated_cost=0.0005,
        temperature=0.2,
    )
    prompts = MagicMock()
    prompts.load.return_value = "Summarize the conversation."

    summarizer = ConversationSummarizer(llm_client=llm, prompt_loader=prompts)
    summary, usage = await summarizer.summarize(
        session_id=uuid4(),
        messages=[{"role": "user", "content": "Explain two sum"}],
    )
    assert "hash map" in summary.lower()
    assert usage["total_tokens"] == 80
