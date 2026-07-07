"""OpenRouter client unit tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from app.clients.openrouter import LLMResponse, OpenRouterClient
from app.core.config import AIServiceSettings


@pytest.fixture
def configured_client() -> OpenRouterClient:
    settings = MagicMock()
    settings.openrouter_api_key = "test-key"
    settings.openrouter_base_url = "https://openrouter.ai/api/v1"
    settings.openrouter_model = "openai/gpt-4o-mini"
    settings.openrouter_timeout_seconds = 30
    ai_settings = AIServiceSettings(
        openrouter_max_retries=1,
        openrouter_retry_backoff_seconds=0.1,
    )
    return OpenRouterClient(settings=settings, ai_settings=ai_settings)


def test_parse_provider() -> None:
    assert OpenRouterClient.parse_provider("openai/gpt-4o-mini") == "openai"
    assert OpenRouterClient.parse_provider("gpt-4") == "unknown"


def test_estimate_cost(configured_client: OpenRouterClient) -> None:
    cost = configured_client.estimate_cost(input_tokens=1000, output_tokens=1000)
    assert cost > 0


def test_is_configured_false() -> None:
    settings = MagicMock()
    settings.openrouter_api_key = None
    client = OpenRouterClient(settings=settings)
    assert client.is_configured is False


@pytest.mark.asyncio
async def test_chat_completion_success(configured_client: OpenRouterClient) -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"teacher":{}}'}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        "model": "openai/gpt-4o-mini",
    }

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.clients.openrouter.httpx.AsyncClient", return_value=mock_client):
        result = await configured_client.chat_completion(
            system_prompt="system",
            user_prompt="user",
        )

    assert isinstance(result, LLMResponse)
    assert result.total_tokens == 30
    assert result.provider == "openai"


@pytest.mark.asyncio
async def test_chat_completion_retries_on_failure(configured_client: OpenRouterClient) -> None:
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("app.clients.openrouter.httpx.AsyncClient", return_value=mock_client),
        patch("app.clients.openrouter.asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(httpx.TimeoutException),
    ):
        await configured_client.chat_completion(system_prompt="s", user_prompt="u")


def test_list_configured_models(configured_client: OpenRouterClient) -> None:
    models = configured_client.list_configured_models()
    assert "openai/gpt-4o-mini" in models
