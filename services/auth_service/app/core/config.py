"""RecentThink Auth Service configuration.

Imports shared settings from :mod:`shared.config` — no duplicated configuration.
"""

from shared.config import Settings, get_settings, settings

SERVICE_NAME: str = "auth_service"
PORT: int = 8001

__all__ = ["PORT", "SERVICE_NAME", "Settings", "get_settings", "settings"]
