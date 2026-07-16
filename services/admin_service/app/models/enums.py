"""Admin Service domain enums."""

from __future__ import annotations

from enum import StrEnum


class AuditAction(StrEnum):
    USER_BLOCKED = "USER_BLOCKED"
    USER_UNBLOCKED = "USER_UNBLOCKED"
    USER_DELETED = "USER_DELETED"
    USER_ACTIVATED = "USER_ACTIVATED"
    USER_DEACTIVATED = "USER_DEACTIVATED"
    SETTINGS_UPDATED = "SETTINGS_UPDATED"
    ANNOUNCEMENT_SENT = "ANNOUNCEMENT_SENT"
    FEATURE_FLAG_CREATED = "FEATURE_FLAG_CREATED"
    FEATURE_FLAG_UPDATED = "FEATURE_FLAG_UPDATED"
    FEATURE_FLAG_DELETED = "FEATURE_FLAG_DELETED"


class NotificationType(StrEnum):
    INFO = "info"
    WARNING = "warning"
    MAINTENANCE = "maintenance"
    ANNOUNCEMENT = "announcement"
    EMERGENCY = "emergency"
    ACCOUNT = "account"
