# Production-ready image for RecentThink auth-service.
# Build from repository root:
#   docker build -f services/auth_service/Dockerfile -t recentthink-auth-service .
#
# Dependencies are installed from the root pyproject.toml (via uv.lock).

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    VIRTUAL_ENV=/opt/venv

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml uv.lock README.md ./
RUN pip install --upgrade pip uv \
    && uv sync --frozen --no-dev --no-install-project

COPY shared/ /app/shared/
COPY services/auth_service/ /app/services/auth_service/

WORKDIR /app/services/auth_service

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
