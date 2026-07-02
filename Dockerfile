# syntax=docker/dockerfile:1
# =============================================================================
# Reusable production image for any RecentThink microservice.
#
# The same Dockerfile builds every service; select the target with build args:
#   docker build \
#     --build-arg SERVICE_NAME=gateway \
#     --build-arg SERVICE_PORT=8000 \
#     -t recentthink-gateway .
#
# `shared` is importable via PYTHONPATH=/app; `app.main` resolves because the
# working directory is the service root. Dependencies are installed from the
# locked root project; the project itself is not installed (--no-install-project).
# =============================================================================
FROM python:3.13-slim AS runtime

ARG SERVICE_NAME
ARG SERVICE_PORT=8000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    VIRTUAL_ENV=/opt/venv \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    SERVICE_PORT=${SERVICE_PORT}

WORKDIR /app

# libpq5 is the runtime library required by psycopg.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install locked dependencies into /opt/venv (uv targets UV_PROJECT_ENVIRONMENT).
COPY pyproject.toml uv.lock README.md ./
RUN pip install --upgrade pip uv \
    && uv sync --frozen --no-dev --no-install-project

# Copy the shared library and only the target service's source.
COPY shared/ /app/shared/
COPY services/${SERVICE_NAME}/ /app/services/${SERVICE_NAME}/

WORKDIR /app/services/${SERVICE_NAME}

EXPOSE ${SERVICE_PORT}

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f\"http://127.0.0.1:{os.environ['SERVICE_PORT']}/\")"

# Shell form so ${SERVICE_PORT} expands at container start.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${SERVICE_PORT}
