#!/bin/sh
# RecentThink container entrypoint.
# Optionally applies Alembic migrations, then execs the service command.
# Set RUN_MIGRATIONS=true to run migrations in-process (migrate job is preferred).
set -eu

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "Applying Alembic migrations..."
  cd /app
  alembic upgrade head
  echo "Migrations applied successfully."
fi

exec "$@"
