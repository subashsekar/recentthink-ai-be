# Docker

Phase 9 packages the entire RecentThink backend so one command starts
PostgreSQL, runs migrations, and brings up every microservice.

## Quick start

```bash
docker compose up --build
# or detached:
docker compose up --build -d
```

When the stack is healthy:

| Endpoint | URL |
|----------|-----|
| Gateway (public API) | http://localhost:8000 |
| Gateway docs | http://localhost:8000/docs |
| PostgreSQL | `localhost:5432` |

Internal services are **not** published to the host. They talk over
`recentthink-network` using Docker DNS names (`auth_service`, `user_service`,
…).

Verify:

```bash
make docker-verify
# or
python scripts/docker-verify.py
```

## Architecture

```
postgres (healthy)
  → migrate (alembic upgrade head, exit 0)
    → auth_service (healthy)
      → user_service (healthy)
        → usage_service (healthy)
          → ai_service (healthy)
            → admin_service (healthy)
              → gateway (healthy, :8000)
```

Compose uses `depends_on` with `condition: service_healthy` (and
`service_completed_successfully` for `migrate`) so nothing starts early.
If migrations fail, the `migrate` container exits non-zero and the rest of
the stack does not start.

## Per-service images

| Service | Dockerfile | Internal port | Host port |
|---------|------------|---------------|-----------|
| `gateway` | `services/gateway/Dockerfile` | 8000 | **8000** |
| `auth_service` | `services/auth_service/Dockerfile` | 8001 | — |
| `user_service` | `services/user_service/Dockerfile` | 8002 | — |
| `admin_service` | `services/admin_service/Dockerfile` | 8003 | — |
| `ai_service` | `services/ai_service/Dockerfile` | 8004 | — |
| `usage_service` | `services/usage_service/Dockerfile` | 8005 | — |
| `migrate` | `docker/migrate.Dockerfile` | — | — (one-shot) |
| `postgres` | `postgres:16-alpine` | 5432 | **5432** |

Every application image:

- Uses `python:3.13-slim` (not Alpine)
- Installs deps with `uv sync --frozen --no-dev`
- Runs as non-root `appuser` (uid 1000)
- Starts Uvicorn with `--host 0.0.0.0` and graceful shutdown
- Defines a `HEALTHCHECK` against `GET /`
- Includes `scripts/docker-entrypoint.sh` (optional `RUN_MIGRATIONS=true`)

Build context is always the **repo root** so `shared/`, `pyproject.toml`, and
`uv.lock` are available. Each service also ships a `.dockerignore` for
documentation; the root `.dockerignore` is what Docker applies.

## Environment variables

Compose loads (when present):

1. `.env` — secrets and host-specific overrides (git-ignored)
2. `.env.docker` — Docker networking defaults (committed)

Compose `environment:` entries always win for critical in-network values
(`DATABASE_URL`, `*_SERVICE_URL`, …). **Never use `localhost` inside
containers** — use service names:

```env
DATABASE_URL=postgresql+psycopg://recentthink:recentthink@postgres:5432/recentthink
AUTH_SERVICE_URL=http://auth_service:8001
USER_SERVICE_URL=http://user_service:8002
ADMIN_SERVICE_URL=http://admin_service:8003
AI_SERVICE_URL=http://ai_service:8004
USAGE_SERVICE_URL=http://usage_service:8005
CACHE_ENABLED=true
CACHE_MAX_ENTRIES=1000
CACHE_DEFAULT_TTL=86400
```

Put API keys (`OPENROUTER_API_KEY`, `SECRET_KEY`, …) in `.env`. For
`ENVIRONMENT=production` / `staging`, `SECRET_KEY` and
`INTERNAL_SERVICE_TOKEN` must not be the insecure defaults.

`LOG_FORMAT=json` (set in `.env.docker`) emits structured JSON logs to the
container stdout. Production also clamps `DEBUG` log level up to `INFO`.

## Volumes

| Volume | Purpose |
|--------|---------|
| `recentthink-postgres-data` | PostgreSQL data |
| `recentthink-logs` | Shared `/app/logs` mount |
| `recentthink-storage` | Local uploads (`user_service` `/app/storage`) |

## Resource limits & restart

Every long-running service uses `restart: unless-stopped`, JSON-file log
rotation (`max-size: 10m`), and Compose `deploy.resources` CPU/memory limits.
Healthchecks retry with `retries: 5`.

## Useful commands

```bash
make docker-build          # docker compose build
make docker-up             # docker compose up -d --build
make docker-down           # docker compose down
make docker-logs           # docker compose logs -f
make docker-verify         # health + print URLs
make db-up                 # postgres only

docker compose up --build              # foreground
docker compose up -d --build           # detached
docker compose restart gateway
docker compose logs -f auth_service
docker compose exec gateway python -c "print('ok')"
docker compose down -v                 # also delete volumes (destructive)
```

## Production notes

- Images are non-root, slim-based, and healthchecked — ready for Kubernetes
  Deployment + Service + Ingress later.
- Migrations are a separate one-shot job (`migrate`) so rollouts can run
  schema updates before new pods accept traffic.
- Uvicorn receives `SIGTERM` and shuts down with
  `--timeout-graceful-shutdown 30`.
- Only expose the gateway (and optionally Postgres) at the edge; keep other
  services on the private network.
