"""DSA Pattern Coach feature adapter package."""

from __future__ import annotations

from app.agents.dsa_pattern.router import router
from app.agents.dsa_pattern.service import DsaPatternService

__all__ = ["DsaPatternService", "router"]
