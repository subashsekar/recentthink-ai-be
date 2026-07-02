"""Alembic migration environment."""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

REPO_ROOT = Path(__file__).resolve().parents[1]
AUTH_SERVICE_ROOT = REPO_ROOT / "services" / "auth_service"

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(AUTH_SERVICE_ROOT))

from app.models.admin import Admin  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401

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
