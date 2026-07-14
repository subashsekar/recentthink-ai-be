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

    # --- In-memory response cache (free; no Redis) ------------------------
    cache_enabled: bool = True
    cache_max_entries: int = Field(default=1000, ge=1)
    cache_default_ttl: int = Field(default=86_400, ge=1)  # 24h
    cache_ttl_leetcode: int = Field(default=86_400, ge=1)
    cache_ttl_hackerrank: int = Field(default=86_400, ge=1)
    cache_ttl_dsa_pattern: int = Field(default=604_800, ge=1)  # 7d
    cache_ttl_course_generator: int = Field(default=2_592_000, ge=1)  # 30d
    cache_ttl_interview: int = Field(default=43_200, ge=1)  # 12h (unused; not cached)

    # Feature-specific OpenRouter completion budgets (override via env as JSON map
    # only if needed — prefer FEATURE_MAX_TOKENS in feature_tokens.py as source).
    feature_max_tokens_leetcode: int = Field(default=1800, ge=1)
    feature_max_tokens_hackerrank: int = Field(default=1800, ge=1)
    feature_max_tokens_dsa_pattern: int = Field(default=3000, ge=1)
    feature_max_tokens_course_generator: int = Field(default=4500, ge=1)
    feature_max_tokens_interview: int = Field(default=2200, ge=1)


from app.core.feature_tokens import FEATURE_MAX_TOKENS as _BUILTIN_FEATURE_MAX_TOKENS


def get_ai_settings() -> AIServiceSettings:
    """Return AI service settings."""
    return AIServiceSettings()


def feature_max_tokens_map(settings: AIServiceSettings | None = None) -> dict[str, int]:
    """Resolve FEATURE_MAX_TOKENS from settings (env-overridable per feature)."""
    cfg = settings or get_ai_settings()
    return {
        **_BUILTIN_FEATURE_MAX_TOKENS,
        "leetcode": cfg.feature_max_tokens_leetcode,
        "hackerrank": cfg.feature_max_tokens_hackerrank,
        "dsa": cfg.feature_max_tokens_dsa_pattern,
        "dsa_pattern": cfg.feature_max_tokens_dsa_pattern,
        "course_generator": cfg.feature_max_tokens_course_generator,
        "course": cfg.feature_max_tokens_course_generator,
        "interview": cfg.feature_max_tokens_interview,
    }


__all__ = [
    "AIServiceSettings",
    "PORT",
    "SERVICE_NAME",
    "Settings",
    "feature_max_tokens_map",
    "get_ai_settings",
    "get_settings",
    "settings",
]
