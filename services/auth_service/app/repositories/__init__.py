"""Data access layer abstractions."""

from app.repositories.admin_repository import AdminRepository
from app.repositories.user_repository import UserRepository

__all__ = ["AdminRepository", "UserRepository"]
