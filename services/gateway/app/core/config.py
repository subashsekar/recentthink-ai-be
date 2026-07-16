"""RecentThink API Gateway configuration.

Imports shared settings from :mod:`shared.config` — no duplicated configuration.
Gateway-specific proxy timeouts and trusted hosts are read from the environment.
"""

from __future__ import annotations

import os

from shared.config import Settings, get_settings, settings

SERVICE_NAME: str = "gateway"
PORT: int = 8000
APP_VERSION: str = "0.1.0"

# Proxy timeouts (seconds). Long read timeout supports streaming AI responses.
PROXY_CONNECT_TIMEOUT: float = float(os.getenv("GATEWAY_CONNECT_TIMEOUT", "5.0"))
PROXY_READ_TIMEOUT: float = float(os.getenv("GATEWAY_READ_TIMEOUT", "120.0"))
PROXY_WRITE_TIMEOUT: float = float(os.getenv("GATEWAY_WRITE_TIMEOUT", "30.0"))
PROXY_POOL_TIMEOUT: float = float(os.getenv("GATEWAY_POOL_TIMEOUT", "5.0"))
PROXY_MAX_RETRIES: int = int(os.getenv("GATEWAY_MAX_RETRIES", "3"))
PROXY_RETRY_BASE_DELAY_S: float = float(os.getenv("GATEWAY_RETRY_BASE_DELAY_S", "0.2"))

# Health probe timeout when checking downstream services.
HEALTH_PROBE_TIMEOUT: float = float(os.getenv("GATEWAY_HEALTH_PROBE_TIMEOUT", "2.0"))

# Session guard: verify JWT + live Auth user state before forwarding.
# Default enabled. Set GATEWAY_SESSION_GUARD_ENABLED=false only for emergencies.
SESSION_GUARD_ENABLED: bool = os.getenv(
    "GATEWAY_SESSION_GUARD_ENABLED", "true"
).strip().lower() in {"1", "true", "yes", "on"}

# Optional gateway-side cache for Auth user-state responses. Default 0 = always
# ask Auth (immediate block/deactivate). Raise slightly under high traffic.
USER_STATE_CACHE_TTL_SECONDS: float = float(
    os.getenv("GATEWAY_USER_STATE_CACHE_TTL_SECONDS", "0")
)

# Comma-separated hosts for TrustedHostMiddleware. Use ``*`` to allow all
# (default for local/test). Production should set explicit hostnames.
_trusted_raw = os.getenv("GATEWAY_TRUSTED_HOSTS", "*")
TRUSTED_HOSTS: list[str] = [
    item.strip() for item in _trusted_raw.split(",") if item.strip()
] or ["*"]

__all__ = [
    "APP_VERSION",
    "HEALTH_PROBE_TIMEOUT",
    "PORT",
    "PROXY_CONNECT_TIMEOUT",
    "PROXY_MAX_RETRIES",
    "PROXY_POOL_TIMEOUT",
    "PROXY_READ_TIMEOUT",
    "PROXY_RETRY_BASE_DELAY_S",
    "PROXY_WRITE_TIMEOUT",
    "SERVICE_NAME",
    "SESSION_GUARD_ENABLED",
    "Settings",
    "TRUSTED_HOSTS",
    "USER_STATE_CACHE_TTL_SECONDS",
    "get_settings",
    "settings",
]
