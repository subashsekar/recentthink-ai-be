# syntax=docker/dockerfile:1
# One-shot migration image: applies Alembic upgrades then exits.
# Needs every service that owns ORM models (see migrations/env.py).
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    VIRTUAL_ENV=/opt/venv \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1000 appuser \
    && useradd --system --uid 1000 --gid appuser --create-home --shell /usr/sbin/nologin appuser

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml uv.lock README.md ./
RUN pip install --upgrade pip uv \
    && uv sync --frozen --no-dev --no-install-project

COPY shared/ /app/shared/
COPY alembic.ini /app/alembic.ini
COPY migrations/ /app/migrations/
COPY services/auth_service/ /app/services/auth_service/
COPY services/user_service/ /app/services/user_service/
COPY services/admin_service/ /app/services/admin_service/
COPY services/ai_service/ /app/services/ai_service/
COPY services/usage_service/ /app/services/usage_service/

RUN chown -R appuser:appuser /app /opt/venv

USER appuser

CMD ["alembic", "upgrade", "head"]
