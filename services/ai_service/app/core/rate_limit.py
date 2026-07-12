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
HACKERRANK_ANALYZE_RATE_LIMIT: str = getattr(_ai_settings, "rate_limit_hackerrank_analyze", "10/minute")
HACKERRANK_FOLLOWUP_RATE_LIMIT: str = getattr(_ai_settings, "rate_limit_hackerrank_followup", "20/minute")
COURSE_GENERATE_RATE_LIMIT: str = getattr(_ai_settings, "rate_limit_course_generate", "5/minute")
COURSE_FOLLOWUP_RATE_LIMIT: str = getattr(_ai_settings, "rate_limit_course_followup", "20/minute")
DSA_PATTERN_GENERATE_RATE_LIMIT: str = getattr(_ai_settings, "rate_limit_dsa_pattern_generate", "5/minute")
DSA_PATTERN_FOLLOWUP_RATE_LIMIT: str = getattr(_ai_settings, "rate_limit_dsa_pattern_followup", "20/minute")
