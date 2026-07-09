# Docker

The whole stack — PostgreSQL plus all six microservices — is defined in
`docker-compose.yml`. Each service has its own `Dockerfile` under
`services/<name>/Dockerfile` (build context is always the repo root).

## Per-service images

| Service | Dockerfile | Port |
|---------|------------|------|
| `gateway` | `services/gateway/Dockerfile` | 8000 |
| `auth_service` | `services/auth_service/Dockerfile` | 8001 |
| `user_service` | `services/user_service/Dockerfile` | 8002 |
| `admin_service` | `services/admin_service/Dockerfile` | 8003 |
| `ai_service` | `services/ai_service/Dockerfile` | 8004 |
| `usage_service` | `services/usage_service/Dockerfile` | 8005 |

Key characteristics:

- Base `python:3.13-slim`; installs `libpq5` for `psycopg`.
- Dependencies installed with `uv sync --frozen --no-dev --no-install-project`
  into `/opt/venv` (via `UV_PROJECT_ENVIRONMENT`).
- Copies `shared/` and the target `services/<name>/` tree into the image.
- `shared` is importable through `PYTHONPATH=/app`; `app.main` resolves because
  the working directory is the service root.
- A `HEALTHCHECK` polls `GET /` on the service port.

Manual build example:

```bash
docker build -f services/gateway/Dockerfile -t recentthink-gateway .
```

## Compose stack

```bash
make docker-build    # docker compose build
make docker-up       # docker compose up -d
make docker-logs     # docker compose logs -f
make docker-down     # docker compose down
make db-up           # start only Postgres
```

What Compose configures:

- **postgres** — `postgres:16-alpine` with a `pg_isready` healthcheck and a
  named volume (`recentthink-postgres-data`).
- **Six services** — each built from `services/<name>/Dockerfile`, published on
  8000–8005.
- **`depends_on` + healthchecks** — every service waits for Postgres to be
  healthy; the gateway additionally waits for the other five services.
- **Networking** — all containers join `recentthink-network` and reach the
  database at host `postgres:5432` and each other by service name.
- **Environment** — a shared YAML anchor injects `ENVIRONMENT`, `LOG_LEVEL`,
  `DATABASE_URL`, `SECRET_KEY`, and the reserved auth/AI variables. Values fall
  back to safe local defaults but can be overridden from your shell or `.env`.

## Verifying the stack

After `make docker-up`:

```bash
docker compose ps
curl http://localhost:8000/         # {"service":"gateway","status":"healthy"}
curl http://localhost:8001/health/db  # {"message":"Database Connected Successfully"}
```

All six ports (8000–8005) should return a healthy payload, and the auth DB
check confirms in-network connectivity to PostgreSQL.

## Notes

- The `DATABASE_URL` inside Compose uses host `postgres` (the service name),
  **not** `localhost`.
- On a host that already runs PostgreSQL on 5432, the container's published
  port may collide; either stop the host instance or change the published port.
- Migrations are not run automatically by Compose. Apply them with
  `make migrate` (locally) or as a deploy step against the target database.
