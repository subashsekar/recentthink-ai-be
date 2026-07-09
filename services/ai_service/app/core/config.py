"""AI Service configuration."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from shared.config import ENV_FILE, Settings, get_settings, settings

SERVICE_NAME: str = "ai_service"
PORT: int = 8004


class AIServiceSettings(BaseSettings):
    """AI-service-specific settings."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    openrouter_max_retries: int = Field(default=3, ge=0, le=10)
    openrouter_retry_backoff_seconds: float = Field(default=1.0, ge=0.1, le=30.0)
    rate_limit_ai_chat: str = "30/minute"
    rate_limit_leetcode_analyze: str = "30/minute"
    rate_limit_leetcode_followup: str = "60/minute"
    prompt_hot_reload: bool = True
    prompt_default_version: str = "v1"
    prompt_default_locale: str = "en"
    available_models: str = (
        "google/gemini-2.5-flash,"
        "deepseek/deepseek-chat,"
        "meta-llama/llama-3.3-70b-instruct,"
        "openai/gpt-4o,"
        "nvidia/llama-3.1-nemotron-ultra-253b-v1"
    )
    model_cost_per_1k_input_tokens: float = 0.00015
    model_cost_per_1k_output_tokens: float = 0.0006
    usd_to_inr_rate: float = Field(default=83.0, ge=1.0)
    openrouter_fallback_model: str = "openai/gpt-4o-mini"
    json_validation_max_retries: int = Field(default=1, ge=0, le=3)
    max_user_message_length: int = 32000


def get_ai_settings() -> AIServiceSettings:
    """Return AI service settings."""
    return AIServiceSettings()


__all__ = [
    "AIServiceSettings",
    "PORT",
    "SERVICE_NAME",
    "Settings",
    "get_ai_settings",
    "get_settings",
    "settings",
]
