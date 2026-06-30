"""RecentThink API Gateway configuration.

Imports shared settings from :mod:`shared.config` — no duplicated configuration.
"""

from shared.config import Settings, get_settings, settings

SERVICE_NAME: str = "gateway"
PORT: int = 8000

__all__ = ["PORT", "SERVICE_NAME", "Settings", "get_settings", "settings"]
