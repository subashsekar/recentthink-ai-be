"""Async OpenRouter API client (OpenAI-compatible)."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import AIServiceSettings, get_ai_settings
from app.utils.cost_calculator import CostCalculator
from shared.config import Settings, get_settings
from shared.logging import get_logger

logger = get_logger(__name__)

_RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


@dataclass(frozen=True)
class LLMResponse:
    """Result of a single LLM completion."""

    content: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    estimated_cost: float
    temperature: float = 0.2

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class OpenRouterClient:
    """Reusable async client for OpenRouter chat completions."""

    def __init__(
        self,
        settings: Settings | None = None,
        ai_settings: AIServiceSettings | None = None,
        cost_calculator: CostCalculator | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._ai_settings = ai_settings or get_ai_settings()
        self._cost = cost_calculator or CostCalculator(settings=self._ai_settings)

    @property
    def is_configured(self) -> bool:
        return bool(self._settings.openrouter_api_key)

    @staticmethod
    def parse_provider(model: str) -> str:
        if "/" in model:
            return model.split("/", 1)[0]
        return "unknown"

    def estimate_cost(self, *, input_tokens: int, output_tokens: int) -> float:
        return self._cost.estimate_request_cost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ).usd

    async def chat_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        fallback_model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        top_p: float | None = None,
        frequency_penalty: float | None = None,
        presence_penalty: float | None = None,
        json_mode: bool = True,
    ) -> LLMResponse:
        if not self.is_configured:
            msg = "OPENROUTER_API_KEY is not configured."
            raise RuntimeError(msg)

        selected_model = model or self._settings.openrouter_model
        fallback = fallback_model or self._ai_settings.openrouter_fallback_model
        models_to_try = [selected_model]
        if fallback and fallback != selected_model:
            models_to_try.append(fallback)

        last_error: Exception | None = None
        for model_index, current_model in enumerate(models_to_try):
            try:
                return await self._request_completion(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=current_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                    frequency_penalty=frequency_penalty,
                    presence_penalty=presence_penalty,
                    json_mode=json_mode,
                )
            except Exception as exc:
                last_error = exc
                if model_index < len(models_to_try) - 1:
                    logger.warning(
                        "openrouter_fallback",
                        extra={"failed_model": current_model, "fallback": models_to_try[-1]},
                    )
                    continue
                raise
        assert last_error is not None
        raise last_error

    async def _request_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        top_p: float | None,
        frequency_penalty: float | None,
        presence_penalty: float | None,
        json_mode: bool,
    ) -> LLMResponse:
        url = f"{self._settings.openrouter_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://recentthink.com",
            "X-Title": "RecentThink AI Service",
        }
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if top_p is not None:
            payload["top_p"] = top_p
        if frequency_penalty is not None:
            payload["frequency_penalty"] = frequency_penalty
        if presence_penalty is not None:
            payload["presence_penalty"] = presence_penalty
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        timeout = httpx.Timeout(self._settings.openrouter_timeout_seconds)
        max_retries = self._ai_settings.openrouter_max_retries
        backoff = self._ai_settings.openrouter_retry_backoff_seconds
        last_error: Exception | None = None
        start = time.perf_counter()
        data: dict[str, Any] = {}

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    if response.status_code in _RETRYABLE_STATUS_CODES:
                        response.raise_for_status()
                    response.raise_for_status()
                    data = response.json()
                break
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code
                if status not in _RETRYABLE_STATUS_CODES or attempt >= max_retries:
                    logger.error(
                        "OpenRouter HTTP error after %s attempts: %s",
                        attempt + 1,
                        exc,
                    )
                    raise
                wait = backoff * (2**attempt)
                logger.warning(
                    "OpenRouter rate limit/temporary failure (status=%s), retrying in %.1fs",
                    status,
                    wait,
                )
                await asyncio.sleep(wait)
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_error = exc
                if attempt >= max_retries:
                    logger.error(
                        "OpenRouter request failed after %s attempts: %s",
                        attempt + 1,
                        exc,
                    )
                    raise
                wait = backoff * (2**attempt)
                logger.warning(
                    "OpenRouter request failed (attempt %s/%s), retrying in %.1fs: %s",
                    attempt + 1,
                    max_retries + 1,
                    wait,
                    exc,
                )
                await asyncio.sleep(wait)
        else:
            assert last_error is not None
            raise last_error

        latency_ms = int((time.perf_counter() - start) * 1000)
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        response_model = str(data.get("model", model))
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        provider = self.parse_provider(response_model)
        cost = self._cost.estimate_request_cost(
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
        )

        return LLMResponse(
            content=content,
            model=response_model,
            provider=provider,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            estimated_cost=cost.usd,
            temperature=temperature,
        )

    async def stream_completion(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        if not self.is_configured:
            msg = "OPENROUTER_API_KEY is not configured."
            raise RuntimeError(msg)

        selected_model = model or self._settings.openrouter_model
        url = f"{self._settings.openrouter_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://recentthink.com",
            "X-Title": "RecentThink AI Service",
        }
        payload: dict[str, Any] = {
            "model": selected_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        timeout = httpx.Timeout(self._settings.openrouter_timeout_seconds)
        async with (
            httpx.AsyncClient(timeout=timeout) as client,
            client.stream("POST", url, headers=headers, json=payload) as response,
        ):
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                chunk = line.removeprefix("data: ").strip()
                if chunk == "[DONE]":
                    break
                yield chunk

    def list_configured_models(self) -> list[str]:
        models = [
            item.strip()
            for item in self._ai_settings.available_models.split(",")
            if item.strip()
        ]
        fallback = self._ai_settings.openrouter_fallback_model
        if fallback and fallback not in models:
            models.append(fallback)
        return models
