"""Alembic migration environment."""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

REPO_ROOT = Path(__file__).resolve().parents[1]
AUTH_SERVICE_ROOT = REPO_ROOT / "services" / "auth_service"
AI_SERVICE_ROOT = REPO_ROOT / "services" / "ai_service"
USAGE_SERVICE_ROOT = REPO_ROOT / "services" / "usage_service"
USER_SERVICE_ROOT = REPO_ROOT / "services" / "user_service"
ADMIN_SERVICE_ROOT = REPO_ROOT / "services" / "admin_service"

sys.path.insert(0, str(REPO_ROOT))


def _clear_app_modules() -> None:
    """Remove cached ``app`` packages so another service can be imported."""
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            sys.modules.pop(name, None)


def _import_auth_models() -> None:
    sys.path.insert(0, str(AUTH_SERVICE_ROOT))
    from app.models.admin import Admin  # noqa: F401
    from app.models.email_verification_token import EmailVerificationToken  # noqa: F401
    from app.models.password_reset_token import PasswordResetToken  # noqa: F401
    from app.models.refresh_token import RefreshToken  # noqa: F401
    from app.models.user import User  # noqa: F401


def _import_ai_models() -> None:
    _clear_app_modules()
    sys.path.insert(0, str(AI_SERVICE_ROOT))
    from app.models.agent_execution import AgentExecution  # noqa: F401
    from app.models.ai_message import AIMessage  # noqa: F401
    from app.models.ai_session import AISession  # noqa: F401
    from app.models.conversation_memory import ConversationMemory  # noqa: F401
    from app.models.course import Course, CourseBookmark, CourseProgress  # noqa: F401
    from app.models.dsa_pattern import (  # noqa: F401
        PatternBookmark,
        PatternMastery,
        PatternProgress,
        PatternSession,
    )
    from app.models.hackerrank_progress import HackerrankProgress  # noqa: F401
    from app.models.leetcode_progress import LeetCodeProgress  # noqa: F401
    from app.models.model_usage import ModelUsage  # noqa: F401
    from app.models.prompt_version import PromptVersion  # noqa: F401


def _import_usage_models() -> None:
    _clear_app_modules()
    sys.path.insert(0, str(USAGE_SERVICE_ROOT))
    from app.models.usage_record import UsageRecord  # noqa: F401


def _import_user_models() -> None:
    _clear_app_modules()
    sys.path.insert(0, str(USER_SERVICE_ROOT))
    from app.models.profile import UserProfile  # noqa: F401


def _import_admin_models() -> None:
    _clear_app_modules()
    sys.path.insert(0, str(ADMIN_SERVICE_ROOT))
    from app.models.audit_log import AdminAuditLog  # noqa: F401
    from app.models.notification import Notification  # noqa: F401


_import_auth_models()
_import_ai_models()
_import_usage_models()
_import_user_models()
_import_admin_models()

from shared.config import get_settings  # noqa: E402
from shared.database import Base, normalize_database_url  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
sqlalchemy_url = normalize_database_url(settings.database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""
    context.configure(
        url=sqlalchemy_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode."""
    connectable = create_engine(sqlalchemy_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
