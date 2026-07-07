"""Rate limiting for AI endpoints."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_ai_settings

_ai_settings = get_ai_settings()

limiter = Limiter(
    key_func=get_remote_address,
    enabled=True,
)

AI_CHAT_RATE_LIMIT: str = _ai_settings.rate_limit_ai_chat
LEETCODE_ANALYZE_RATE_LIMIT: str = _ai_settings.rate_limit_leetcode_analyze
LEETCODE_FOLLOWUP_RATE_LIMIT: str = _ai_settings.rate_limit_leetcode_followup
