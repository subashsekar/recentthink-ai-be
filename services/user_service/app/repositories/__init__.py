"""User Service repositories."""

from app.repositories.profile_repository import ProfileRepository
from app.repositories.statistics_repository import StatisticsRepository, UserStatistics

__all__ = ["ProfileRepository", "StatisticsRepository", "UserStatistics"]
