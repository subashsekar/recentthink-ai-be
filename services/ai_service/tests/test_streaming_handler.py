"""Streaming handler unit tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.streaming_handler import StreamingHandler


@pytest.mark.asyncio
async def test_stream_yields_chunks() -> None:
    llm = MagicMock()

    async def _stream(**_kwargs: object):
        yield "chunk-1"
        yield "chunk-2"

    llm.stream_completion = _stream
    handler = StreamingHandler(llm_client=llm)
    chunks = [chunk async for chunk in handler.stream(system_prompt="s", user_prompt="u")]
    assert chunks == ["chunk-1", "chunk-2"]
