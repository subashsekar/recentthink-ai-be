# RecentThink

A production-ready SaaS AI platform built as a **microservice monorepo** with **clean architecture**. Each service is an independent FastAPI application sharing configuration, database utilities, and cross-cutting concerns through the `shared/` package.

**Phase 1 status:** Foundation complete — health endpoints, shared config, SQLAlchemy models, Alembic migrations, repository layer, Docker, and CI are in place. JWT authentication, API Gateway routing, and business HTTP APIs arrive in later phases.

---

## Project Overview

RecentThink is designed to scale from a local development setup to a multi-service cloud deployment. The repository contains six deployable microservices plus shared infrastructure code:

| Service | Port | Responsibility |
|---------|------|----------------|
| **gateway** | 8000 | Single entry point for clients; request routing (later) |
| **auth_service** | 8001 | Authentication, users, admins, tokens (in progress) |
| **user_service** | 8002 | User profiles and account data (later) |
| **admin_service** | 8003 | Admin dashboards and RBAC (later) |
| **ai_service** | 8004 | AI agents, LLM orchestration, RAG (later) |
| **usage_service** | 8005 | Metering, quotas, billing usage (later) |

The **auth_service** is the most developed service today: it owns `User` and `Admin` ORM models, repositories, Alembic migrations, and a database connectivity endpoint.

---

## Architecture

### High-level diagram

```
                    ┌─────────────┐
                    │   Gateway   │  :8000
                    │  (routing)  │
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │ auth_service│ │ user_service│ │ admin_service│
    │    :8001    │ │    :8002    │ │    :8003    │
    └──────┬──────┘ └─────────────┘ └─────────────┘
           │
           ▼
    ┌─────────────┐ ┌─────────────┐
    │  ai_service │ │usage_service│
    │    :8004    │ │    :8005    │
    └─────────────┘ └─────────────┘
           │
           ▼
    ┌─────────────────────────────────┐
    │  PostgreSQL (local or Supabase) │
    └─────────────────────────────────┘
```

### Clean architecture (per service)

Each microservice follows the same inward dependency flow:

```
HTTP Request
    │
    ▼
api/            ← HTTP routers (thin handlers)
    │
    ▼
services/       ← Business logic and use-case orchestration
    │
    ▼
repositories/   ← Data access (SQLAlchemy queries)
    │
    ▼
models/         ← Domain / ORM models
```

Supporting layers:

| Layer | Responsibility |
|-------|----------------|
| `main.py` | App factory, lifespan, router wiring only |
| `schemas/` | Pydantic request/response DTOs |
| `dependencies/` | FastAPI dependency injection (DB session, repos) |
| `middleware/` | Cross-cutting HTTP concerns |
| `core/` | Service identity (`SERVICE_NAME`, `PORT`) |
| `database/` | Re-exports from `shared.database` (auth_service) |

**Naming note:** the repo root `services/` folder holds **microservices** (deployable apps). Inside each microservice, `app/services/` is the **business-logic layer**. They are different concepts.

### Shared package

Code used by two or more services lives in `shared/` at the repository root — configuration, database session, logging, security helpers, base models, and shared schemas (e.g. health responses).

### Database migrations

Alembic runs at the **repository root** (not per-service). `migrations/env.py` imports ORM models from `auth_service` because that service currently owns the schema. As other services gain their own tables, their models must be registered in `migrations/env.py`.

---

## Folder Structure

```
recentthink-ai-be/
├── .github/workflows/       # CI pipelines (lint, type-check, test)
├── infrastructure/          # Deployment placeholders (k8s, nginx, terraform)
├── migrations/              # Alembic migrations (root-level)
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── scripts/                 # Developer utilities (seed, scaffold)
├── services/                # Independent microservices
│   ├── gateway/
│   ├── auth_service/        # Dockerfile, domain models, repositories
│   ├── user_service/
│   ├── admin_service/
│   ├── ai_service/
│   └── usage_service/
├── shared/                  # Cross-service code
│   ├── config.py
│   ├── database/
│   ├── exceptions/
│   ├── logging/
│   ├── models/
│   ├── schemas/
│   └── security/
├── tests/                   # Root-level tests (config, CRUD integration)
├── .env.example
├── alembic.ini
├── docker-compose.yml
├── Makefile
├── pyproject.toml
└── uv.lock
```

### Per-service layout

Every microservice follows this structure:

```
services/<name>/
├── app/
│   ├── main.py              # Composition root
│   ├── api/                 # HTTP route handlers
│   ├── core/                # SERVICE_NAME, PORT, config import
│   ├── services/            # Business logic layer
│   ├── repositories/        # Data access layer
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic DTOs
│   ├── dependencies/        # FastAPI DI providers
│   ├── middleware/          # HTTP middleware
│   ├── database/            # DB re-exports (auth_service only)
│   └── utils/               # Service-specific helpers
├── tests/
└── Dockerfile               # auth_service only; deps from root pyproject.toml
```

---

## Folder Reference

### Repository root

| Path | Purpose |
|------|---------|
| `alembic.ini` | Alembic configuration; `script_location = migrations` |
| `docker-compose.yml` | Local dev stack: auth-service + optional PostgreSQL |
| `pyproject.toml` | Project metadata, dependencies, tool config |
| `uv.lock` | Locked dependency versions |
| `Makefile` | Developer shortcuts (run, test, migrate, docker) |
| `.env.example` | Template for environment variables (copy to `.env`) |

### `migrations/`

| Path | Purpose |
|------|---------|
| `env.py` | Alembic runtime: loads `DATABASE_URL`, registers ORM metadata |
| `script.py.mako` | Template for new revision files |
| `versions/` | One Python file per schema migration |

### `scripts/`

| Script | Purpose |
|--------|---------|
| `seed_admin.py` | Inserts default admin (`admin@recentthink.ai`) if missing |
| `scaffold_layers.py` | One-off generator for empty layer `__init__.py` files |
| `align_service_layers.py` | One-off synchroniser for health boilerplate |

### `shared/`

| Path | Purpose |
|------|---------|
| `config.py` | Central Pydantic `Settings` — single source of truth for env vars |
| `database/` | SQLAlchemy `Base`, engine, `SessionLocal`, `get_db()` dependency |
| `models/` | Abstract base ORM mixins (`TimestampMixin`, `BaseModel`) |
| `exceptions/` | Shared repository errors (`DuplicateEmailError`, etc.) |
| `logging/` | Structured logger factory (`get_logger`) |
| `schemas/` | Cross-service Pydantic schemas (`HealthResponse`) |
| `security/` | Password hashing (`hash_password`, `verify_password`) |
| `constants/` | App-wide constants (reserved for future use) |
| `utils/` | Shared utility functions (reserved for future use) |
| `common/` | Miscellaneous shared helpers (reserved for future use) |

### `services/<name>/app/` layers

| Path | Purpose |
|------|---------|
| `api/` | FastAPI routers — parse HTTP, call service layer, return schemas |
| `services/` | Business logic — validation, orchestration, domain rules |
| `repositories/` | Persistence — SQLAlchemy queries, no business rules |
| `models/` | SQLAlchemy ORM table definitions |
| `schemas/` | Pydantic models for request/response serialization |
| `dependencies/` | FastAPI `Depends()` providers (DB session, repositories) |
| `middleware/` | Request/response middleware (auth, logging, CORS — later) |
| `core/` | Service-specific constants (`SERVICE_NAME`, `PORT`) |
| `database/` | Thin re-export of `shared.database` (auth_service) |
| `utils/` | Helpers that belong only to this service |
| `main.py` | Creates the FastAPI app and mounts routers |

### `infrastructure/`

Placeholder directories for future deployment assets: Docker configs, Kubernetes manifests, Nginx, monitoring, Terraform.

### `tests/`

| Path | Purpose |
|------|---------|
| `test_config.py` | Shared settings smoke tests |
| `crud/` | Integration tests for auth_service repositories |

---

## Technology Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.13 |
| Web framework | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |
| Database | PostgreSQL (local Docker or Supabase) |
| Driver | psycopg 3 |
| Configuration | Pydantic Settings + python-dotenv |
| Password hashing | bcrypt |
| Package manager | uv |
| Testing | pytest + pytest-cov + httpx |
| Linting / formatting | Ruff, Black, isort |
| Type checking | mypy |
| Containers | Docker + Docker Compose |
| CI | GitHub Actions |

---

## Installation

### Prerequisites

- Python 3.13
- [uv](https://docs.astral.sh/uv/) package manager
- PostgreSQL (local via Docker, or Supabase)
- Docker Desktop (optional, for containerised development)

### 1. Clone the repository

```bash
git clone <repository-url>
cd recentthink-ai-be
```

### 2. Install uv

**macOS / Linux:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 3. Install dependencies

```bash
uv sync --all-groups
```

This creates a `.venv` virtual environment and installs all runtime and dev dependencies from `uv.lock`.

### 4. Configure environment

```bash
cp .env.example .env        # Windows: copy .env.example .env
```

Edit `.env` with your database URL and secrets. See [Environment Variables](#environment-variables) below.

### 5. Start PostgreSQL

**Option A — Docker (recommended for local dev):**

```bash
docker compose --profile local-db up -d postgres
```

**Option B — Supabase:** set `DATABASE_URL` in `.env` to your Supabase connection string. No local postgres needed.

### 6. Run migrations

```bash
uv run alembic upgrade head
# or: make migrate
```

### 7. Seed the default admin (optional)

```bash
uv run python scripts/seed_admin.py
# or: make seed-admin
```

Default credentials: `admin@recentthink.ai` / password from `SEED_ADMIN_PASSWORD` (default `Admin@12345`).

### 8. Verify

```bash
uv run pytest
```

---

## Environment Variables

All variables are defined in `shared/config.py` and loaded from the process environment and an optional `.env` file. Copy `.env.example` to `.env` and adjust.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | No | `local` | Deployment environment (`local`, `development`, `staging`, `production`, `test`) |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `DATABASE_URL` | No | `postgresql+psycopg://recentthink:recentthink@localhost:5432/recentthink` | PostgreSQL connection string |
| `SECRET_KEY` | Yes (prod) | `change-me-in-production` | Application secret for signing tokens |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | Access token lifetime |
| `OPENAI_API_KEY` | No | — | OpenAI API key (future) |
| `GOOGLE_API_KEY` | No | — | Google API key (future) |
| `SEED_ADMIN_PASSWORD` | No | `Admin@12345` | Password for `scripts/seed_admin.py` |
| `AUTH_SERVICE_PORT` | No | `8001` | Host port for auth-service in Docker Compose |
| `POSTGRES_USER` | No | `recentthink` | Local postgres user (Docker) |
| `POSTGRES_PASSWORD` | No | `recentthink` | Local postgres password (Docker) |
| `POSTGRES_DB` | No | `recentthink` | Local postgres database name (Docker) |
| `POSTGRES_PORT` | No | `5432` | Host port for postgres in Docker Compose |

**Never commit `.env`** — it is listed in `.gitignore`.

**Docker note:** when running auth-service inside Docker with the `local-db` profile, set `DATABASE_URL` to use hostname `postgres` instead of `localhost`.

---

## Docker Commands

### Auth service only (external / Supabase database)

```bash
docker compose up --build auth-service
```

### Auth service + local PostgreSQL

```bash
docker compose --profile local-db up --build
```

### Detached mode

```bash
docker compose --profile local-db up --build -d
```

### View logs

```bash
docker compose logs -f auth-service
```

### Stop containers

```bash
docker compose --profile local-db down
```

### Build image without starting

```bash
docker build -f services/auth_service/Dockerfile -t recentthink-auth-service .
```

### Verify health

```bash
curl http://localhost:8001/health
# {"service":"auth_service","status":"healthy"}

curl http://localhost:8001/
# {"message":"Database Connected Successfully"}
```

Hot reload is enabled in `docker-compose.yml` via volume mounts on `shared/` and `services/auth_service/`.

---

## Alembic Commands

All commands run from the **repository root**.

| Command | Description |
|---------|-------------|
| `uv run alembic upgrade head` | Apply all pending migrations |
| `uv run alembic downgrade -1` | Roll back one revision |
| `uv run alembic current` | Show current revision |
| `uv run alembic history` | List all revisions |
| `uv run alembic revision --autogenerate -m "description"` | Generate a new migration from model changes |

Makefile shortcut:

```bash
make migrate    # equivalent to: uv run alembic upgrade head
```

**Adding models from a new service:** import the model classes in `migrations/env.py` so Alembic can detect them during autogenerate.

---

## Run Locally

Start any service from the repository root by changing into its directory:

```bash
cd services/auth_service
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Or use Makefile shortcuts (Unix / Git Bash):

| Command | Service | Port |
|---------|---------|------|
| `make run-gateway` | API Gateway | 8000 |
| `make run-auth` | Auth Service | 8001 |
| `make run-user` | User Service | 8002 |
| `make run-admin` | Admin Service | 8003 |
| `make run-ai` | AI Service | 8004 |
| `make run-usage` | Usage Service | 8005 |

### Health endpoints

| Service | Health URL |
|---------|------------|
| gateway | `GET http://localhost:8000/` |
| auth_service | `GET http://localhost:8001/health` |
| auth_service (DB) | `GET http://localhost:8001/` |
| user_service | `GET http://localhost:8002/` |
| admin_service | `GET http://localhost:8003/` |
| ai_service | `GET http://localhost:8004/` |
| usage_service | `GET http://localhost:8005/` |

### Quality gates

```bash
make check          # lint + format-check + typecheck + test
uv run pytest       # run tests only
uv run ruff check . # lint only
```

---

## Deployment Notes

- **auth_service** has a production Dockerfile at `services/auth_service/Dockerfile` (Python 3.13, virtualenv, Uvicorn).
- Other services will receive Dockerfiles in a later phase.
- Environment variables must be injected at runtime — never bake secrets into images.
- Set `ENVIRONMENT=production` and a strong `SECRET_KEY` in production.
- Run `alembic upgrade head` as a deployment step before starting services.
- The shared `DATABASE_URL` supports Supabase connection strings; `normalize_database_url()` in `shared/database/session.py` handles `postgresql://` and pgbouncer query params.
- CI runs on every push/PR to `main`: Ruff, isort, Black, mypy, and pytest with coverage.

---

## Future Roadmap

| Phase | Focus |
|-------|-------|
| **Phase 1** (current) | Microservice scaffold, shared config, health checks, DB layer, Docker, CI |
| **Phase 2** | JWT authentication, login/register endpoints, password verification |
| **Phase 3** | API Gateway routing, service-to-service communication |
| **Phase 4** | User profiles, admin dashboards, RBAC |
| **Phase 5** | AI agents, LLM orchestration, RAG pipelines |
| **Phase 6** | Usage metering, quotas, billing integration |
| **Phase 7** | Kubernetes manifests, monitoring, production hardening |

---

## Fresh Clone Checklist

Run these steps after cloning to confirm everything works:

```bash
# 1. Install dependencies
uv sync --all-groups

# 2. Configure environment
cp .env.example .env

# 3. Start local database
docker compose --profile local-db up -d postgres

# 4. Apply migrations
uv run alembic upgrade head

# 5. Seed admin (optional)
uv run python scripts/seed_admin.py

# 6. Run tests
uv run pytest

# 7. Start auth service
cd services/auth_service
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 8. Verify (in another terminal)
curl http://localhost:8001/health
curl http://localhost:8001/
```

---

## License

Proprietary — RecentThink Team.
