# RecentThink

Portfolio **microservice AI platform** for interview and coding practice
mentorship. Six FastAPI services sit behind an API Gateway, with shared
configuration, PostgreSQL persistence, JWT auth, admin tooling, usage metering,
and streaming chat over SSE.

**Products (AI Service):** LeetCode Mentor, HackerRank Mentor, DSA Pattern Coach,
Course Generator. Chat/SSE streaming is available under `/chat/{feature}/*`.
AI Service completion: **~95%** — see
[docs/AI_SERVICE_COMPLETION_REPORT.md](docs/AI_SERVICE_COMPLETION_REPORT.md).
Interview Trainer is intentionally **not** implemented (out of scope for this
portfolio).

## Technology stack

| Concern | Choice |
|--------------------------|-----------------------------------------|
| Language | Python 3.13 |
| Web framework | FastAPI + Uvicorn |
| ORM / migrations | SQLAlchemy 2.x + Alembic |
| Database | PostgreSQL 16 (via `psycopg` 3) |
| Configuration | Pydantic Settings (`shared/config.py`) |
| Packaging / environments | uv |
| AI orchestration | LangGraph + OpenRouter |
| Auth | JWT (HS256), refresh rotation, bcrypt |
| Inter-service auth | `X-Internal-Service-Token` |
| Testing | Pytest, pytest-asyncio, pytest-cov |
| Quality | Ruff, Black, isort, mypy (strict) |
| Containers | Docker + Docker Compose |
| Monitoring | Sentry (optional) |

## Folder structure

```
recentthink/
├── services/                 # One folder per microservice (each may include Dockerfile)
│   ├── gateway/              # API gateway               (:8000)
│   ├── auth_service/         # Auth + identity           (:8001)
│   ├── user_service/         # Profiles / avatars        (:8002)
│   ├── admin_service/        # Admin aggregation         (:8003)
│   ├── ai_service/           # AI products + chat/SSE    (:8004)
│   ├── usage_service/        # Usage metering            (:8005)
│   └── conftest.py           # Cross-service test isolation
│   # each service: app/{api,core,services,repositories,models,
│   #                     schemas,dependencies,middleware,utils}, tests/
├── shared/                   # Reusable library shared by all services
│   ├── config.py             # Pydantic BaseSettings (single source of truth)
│   ├── database/             # Engine, SessionLocal, Base, get_db
│   ├── models/               # TimestampedModel + mixins
│   ├── schemas/              # Shared Pydantic schemas (health, ...)
│   ├── security/             # Passwords, JWT, service token
│   ├── exceptions/           # Domain exception types
│   ├── logging/              # Logger factory
│   ├── constants/ utils/ common/
│   └── py.typed              # PEP 561 marker (shared ships type hints)
├── migrations/               # Alembic environment + versioned migrations
├── infrastructure/           # IaC / deployment placeholders
├── scripts/                  # Operational scripts (e.g. seed_admin.py)
├── docs/                     # Architecture & workflow documentation
├── tests/                    # Root + CRUD integration tests
├── .github/workflows/        # CI pipeline
├── docker-compose.yml        # Postgres + migrate + all six services
├── .env.docker               # Docker networking defaults (safe to commit)
├── docker/migrate.Dockerfile # One-shot Alembic migration image
├── alembic.ini
├── pyproject.toml            # Deps + tool config (Ruff/Black/isort/mypy/pytest)
├── Makefile
└── uv.lock
```

More detail lives in [`docs/`](docs/): [architecture](docs/architecture.md),
[database](docs/database.md), [environment](docs/environment.md),
[docker](docs/docker.md), [development](docs/development.md),
[testing](docs/testing.md), [conversation chat](docs/conversation-chat.md),
[backend completion](docs/BACKEND_COMPLETION_REPORT.md).

## Microservice architecture

Each service is a self-contained FastAPI application following clean
architecture layering inside `app/`:

- `api/` — HTTP routes (delivery layer)
- `services/` — use-case / business logic
- `repositories/` — data access (SQLAlchemy)
- `models/` — ORM entities
- `schemas/` — Pydantic request/response models
- `core/` — service-local configuration (name, port)
- `dependencies/`, `middleware/`, `utils/` — cross-cutting concerns

All services import configuration and infrastructure from the `shared`
package, so there is no duplicated config or database wiring.

### Ports

| Service | Port | `GET /` health | Docker host publish |
|-----------------|------|----------------|---------------------|
| Gateway | 8000 | ✅ | **yes** (`:8000`) |
| Auth Service | 8001 | ✅ (+ `GET /health/db`) | internal only |
| User Service | 8002 | ✅ | internal only |
| Admin Service | 8003 | ✅ | internal only |
| AI Service | 8004 | ✅ | internal only |
| Usage Service | 8005 | ✅ | internal only |
| PostgreSQL | 5432 | `pg_isready` | **yes** (`:5432`) |

Every service exposes `GET /` returning `{"service": "<name>", "status": "healthy"}`.
In Docker, call non-gateway services through the gateway or via `docker compose exec`.

## Getting started

### 1. Install uv

**macOS / Linux:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Alternatively `pip install uv`. Verify with `uv --version`.

### 2. Install dependencies

Creates `.venv/` and installs everything (incl. dev tools) from `uv.lock`,
provisioning Python 3.13 automatically if needed:

```bash
uv sync --all-groups        # or: make install
```

### 3. Configure environment variables

Keep secrets in a git-ignored `.env` (API keys, `SECRET_KEY`, etc.). Docker
Compose also loads the committed [`.env.docker`](.env.docker) overlay for
in-network URLs (`postgres`, `auth_service`, …). Do not point container
`DATABASE_URL` or `*_SERVICE_URL` at `localhost`.

See [`docs/environment.md`](docs/environment.md) for the full catalog.

## Running the services

Run any service locally (hot reload). Use the Makefile or the raw `uv` command:

```bash
make run-gateway             # cd services/gateway && uv run uvicorn app.main:app --reload --port 8000
make run-auth                # :8001
make run-user                # :8002
make run-admin               # :8003
make run-ai                  # :8004
make run-usage               # :8005
```

Interactive docs for a running service are at `http://localhost:<port>/docs`.

## Running everything with Docker

One command starts PostgreSQL, applies Alembic migrations, and brings up every
backend service plus the gateway:

```bash
docker compose up --build
# detached:
docker compose up --build -d
```

Makefile helpers:

```bash
make docker-build            # docker compose build
make docker-up               # docker compose up -d --build
make docker-logs             # tail logs
make docker-down             # docker compose down
make docker-verify           # health checks + print service URLs
```

What you get:

- **Published ports** — Gateway `http://localhost:8000`, PostgreSQL `localhost:5432`
- **Internal network** — `recentthink-network`; services reach each other by name
  (e.g. `http://auth_service:8001`), never `localhost`
- **Startup order** — postgres → migrate → auth → user → usage → ai → admin → gateway
- **Health waits** — `depends_on` with `condition: service_healthy` /
  `service_completed_successfully`
- **Env** — `.env` (secrets) + `.env.docker` (Docker networking defaults)

See [`docs/docker.md`](docs/docker.md) for rebuild, logs, volumes, resource
limits, and production notes.

## Database & migrations (Alembic)

```bash
make migrate                 # alembic upgrade head
make migrate-down            # alembic downgrade -1
make migrate-history         # alembic history --verbose
make migrate-revision m="add widgets table"   # autogenerate a revision
make seed-admin              # create the default administrator
```

The Alembic environment reads `DATABASE_URL` from `shared.config`. See
[`docs/database.md`](docs/database.md).

## Testing

```bash
make test                    # uv run pytest (root + service + CRUD tests)
make coverage                # + HTML report in htmlcov/
uv run pytest -m "not db"    # skip tests that require a live database
```

CRUD tests are marked `db` and require PostgreSQL. Start one first
(`make db-up`) or run the full stack. See [`docs/testing.md`](docs/testing.md).

## Code quality

```bash
make lint                    # uv run ruff check .
make format                  # uv run isort .  &&  uv run black .
make format-check            # verify formatting only
make typecheck               # mypy: shared + tests + each service's app
make check                   # lint + format-check + typecheck + test
```

Individual tools:

```bash
uv run ruff check .
uv run isort .        # sort imports
uv run black .        # format
uv run mypy shared tests
```

## Environment variables

Defined in `.env` (secrets, git-ignored) and `.env.docker` (Docker networking
defaults). Loaded via Pydantic `BaseSettings` in `shared/config.py`, with
Compose `environment:` overriding in-network URLs inside containers.

| Variable | Purpose |
|-------------------------------|--------------------------------------------|
| `ENVIRONMENT` | `local` / `development` / `staging` / `production` / `test` |
| `LOG_LEVEL` | Logging level (`INFO`, `DEBUG`, ...) |
| `DATABASE_URL` | PostgreSQL DSN (`postgresql+psycopg://...`) |
| `SECRET_KEY` | JWT signing secret; **must** be set outside local/test |
| `INTERNAL_SERVICE_TOKEN` | Shared secret for service-to-service calls |
| `AUTH_SERVICE_URL` … `USAGE_SERVICE_URL` | Inter-service base URLs |
| `OPENROUTER_API_KEY` | OpenRouter API key for AI Service |

Full catalog: [`docs/environment.md`](docs/environment.md). `.env` is
git-ignored; never commit real secrets. The application **fails fast** if
`SECRET_KEY` or `INTERNAL_SERVICE_TOKEN` stay at insecure defaults outside
local/test.
