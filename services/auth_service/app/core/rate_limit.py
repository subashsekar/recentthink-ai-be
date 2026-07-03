"""Rate limiting for unauthenticated authentication endpoints.

Uses ``slowapi`` to apply per-IP throttling to ``/auth/login`` and
``/auth/register``, protecting against credential brute-forcing and
registration abuse.

This is intentionally self-contained: limits and the enabled flag are driven by
:class:`shared.config.Settings`. Once an API gateway owns edge rate limiting,
set ``RATE_LIMIT_ENABLED=false`` to disable this layer without touching the
route or service code.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from shared.config import get_settings

_settings = get_settings()

# ``headers_enabled`` is left off: injecting ``X-RateLimit-*`` headers would
# require every rate-limited route to expose a ``Response`` object. The 429
# response from the shared exception handler is sufficient for our needs.
limiter = Limiter(
    key_func=get_remote_address,
    enabled=_settings.rate_limit_enabled,
)

LOGIN_RATE_LIMIT: str = _settings.rate_limit_login
REGISTER_RATE_LIMIT: str = _settings.rate_limit_register
