"""User Service FastAPI dependencies."""

from app.dependencies.auth import (
    AuthenticatedUser,
    get_current_user,
    require_admin_user,
    require_authenticated_user,
)
from app.dependencies.repositories import (
    get_avatar_service,
    get_profile_service,
    get_public_profile_service,
    get_statistics_service,
)

__all__ = [
    "AuthenticatedUser",
    "get_avatar_service",
    "get_current_user",
    "get_profile_service",
    "get_public_profile_service",
    "get_statistics_service",
    "require_admin_user",
    "require_authenticated_user",
]
