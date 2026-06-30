# RecentThink

A production-ready SaaS AI application built on a **microservice** + **clean
architecture** foundation. Each service is an independent FastAPI application
with a health endpoint, shared configuration, and a layered folder structure
ready for authentication, business logic, AI workloads, and persistence in
later phases.

## Tech stack

- **Python 3.13**
- **FastAPI** + **Uvicorn**
- **SQLAlchemy 2.x** + **Alembic** (to be configured later)
- **PostgreSQL** (via `psycopg`)
- **Pydantic Settings** for configuration
- **uv** for dependency & environment management
- **Pytest** (+ coverage) for testing
- **Ruff**, **Black**, **isort**, **mypy** for quality gates
- **Docker Compose** for local infrastructure

## Microservice architecture

RecentThink is split into **independently deployable services**. Each service
owns a bounded domain, runs on its own port, and communicates over HTTP (via
the API Gateway in later phases). Shared code lives in the `shared/` package so
configuration, logging, and cross-cutting concerns are not duplicated.

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
    └─────────────┘ └─────────────┘ └─────────────┘
           ▼               ▼
    ┌─────────────┐ ┌─────────────┐
    │  ai_service │ │usage_service│
    │    :8004    │ │    :8005    │
    └─────────────┘ └─────────────┘
```

## Service responsibilities

| Service | Port | Responsibility |
|---------|------|----------------|
| **gateway** | 8000 | Single entry point for clients; request routing and aggregation (later) |
| **auth_service** | 8001 | Authentication, tokens, and session management (later) |
| **user_service** | 8002 | User profiles, preferences, and account data (later) |
| **admin_service** | 8003 | Admin dashboards, tenant management, and RBAC (later) |
| **ai_service** | 8004 | AI agents, LLM orchestration, and RAG pipelines (later) |
| **usage_service** | 8005 | Metering, quotas, and billing-related usage tracking (later) |

## Project structure

```
recentthink/
├── services/                    # Independent microservices
│   ├── gateway/
│   ├── auth_service/
│   ├── user_service/
│   ├── admin_service/
│   ├── ai_service/
│   └── usage_service/
│       ├── app/                 # Application code (clean architecture layers)
│       │   ├── api/             # HTTP routers
│       │   ├── core/            # Service config (imports shared/config.py)
│       │   ├── services/        # Business logic
│       │   ├── repositories/  # Data access
│       │   ├── models/          # Domain / ORM models
│       │   ├── schemas/         # Pydantic request/response schemas
│       │   ├── dependencies/    # FastAPI dependencies
│       │   ├── middleware/      # HTTP middleware
│       │   ├── utils/           # Service-specific helpers
│       │   └── main.py          # Composition root only (wires routers, no business logic)
│       └── tests/               # Service-level tests
├── shared/                      # Code shared across all services
│   ├── config.py                # Central Pydantic settings (single source of truth)
│   ├── database/                # DB session & engine helpers (later)
│   ├── exceptions/              # Shared exception types (later)
│   ├── constants/               # App-wide constants (later)
│   ├── schemas/                 # Cross-service schemas (later)
│   ├── models/                  # Shared models (later)
│   ├── security/                # Crypto & auth helpers (later)
│   ├── utils/                   # Shared utilities (later)
│   ├── logging/                 # Structured logging (later)
│   └── common/                  # Miscellaneous shared code (later)
├── infrastructure/              # Deployment & operations (placeholders)
│   ├── docker/
│   ├── nginx/
│   ├── monitoring/
│   ├── logging/
│   ├── scripts/
│   ├── terraform/
│   └── kubernetes/
├── tests/                       # Root-level shared tests (e.g. config)
├── scripts/                     # Developer scripts
├── .github/workflows/           # CI pipelines
├── .env.example                 # Sample environment configuration
├── pyproject.toml
├── docker-compose.yml
├── Makefile
└── uv.lock
```

## Clean architecture layers

> **Naming note:** the repo root `services/` folder holds **microservices**
> (deployable apps). Inside each microservice, `app/services/` is the
> **business-logic layer** (use cases). They are different things.

Each microservice follows the same inward dependency flow:

```
HTTP Request
    │
    ▼
api/            ← HTTP routers only (thin handlers)
    │
    ▼
services/       ← Business logic and use-case orchestration
    │
    ▼
repositories/   ← Data access (SQLAlchemy queries, later)
    │
    ▼
models/         ← Domain / ORM models
```

Supporting layers:

| Layer | Responsibility | Must NOT contain |
|-------|----------------|------------------|
| **`main.py`** | App factory, lifespan, router wiring | Business logic, SQL, HTTP handlers |
| **`api/`** | Route definitions, call service layer | Business rules, DB access |
| **`schemas/`** | Pydantic request/response DTOs | Business logic |
| **`services/`** | **All business logic** | HTTP details, raw SQL |
| **`repositories/`** | Persistence queries | Business rules |
| **`dependencies/`** | FastAPI DI (DB session, auth context) | Business logic |
| **`middleware/`** | Cross-cutting HTTP concerns | Domain logic |
| **`core/`** | Service identity (`SERVICE_NAME`, `PORT`) + shared config import | Business logic |

**Example (health check — already implemented):**

```
GET /
  → api/health.py          calls get_health_status()
  → services/health_service.py   builds the health payload
  → schemas/health.py      defines HealthResponse
```

When you add features (e.g. user registration), the flow should be:

```
POST /users
  → api/users.py
  → services/user_service.py      (validate, orchestrate)
  → repositories/user_repository.py
  → models/user.py
```

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

Verify with `uv --version`.

### 2. Sync dependencies

```bash
uv sync --all-groups
```

### 3. Configure environment variables

```bash
cp .env.example .env   # Windows: copy .env.example .env
```

Never commit `.env` — it is listed in `.gitignore`. Only `.env.example` is tracked.

### 4. Run a service individually

From the repository root, `cd` into the service directory and start Uvicorn.
Each service exposes `GET /` returning `{"service": "<name>", "status": "healthy"}`.

**Gateway (port 8000):**

```bash
cd services/gateway
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Auth Service (port 8001):**

```bash
cd services/auth_service
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

**User Service (port 8002):**

```bash
cd services/user_service
uv run uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

**Admin Service (port 8003):**

```bash
cd services/admin_service
uv run uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

**AI Service (port 8004):**

```bash
cd services/ai_service
uv run uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload
```

**Usage Service (port 8005):**

```bash
cd services/usage_service
uv run uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
```

On macOS/Linux you can also use Makefile shortcuts: `make run-gateway`, `make run-auth`, etc.

Verify health:

```bash
curl http://localhost:8001/
# {"service":"auth_service","status":"healthy"}
```

## Running tests

Run the full suite from the repository root:

```bash
uv run pytest
```

Run tests for a single service:

```bash
uv run pytest services/auth_service/tests/
```

Each service includes a smoke test that asserts `GET /` returns HTTP 200.

## Common commands

| Command | Description |
|---------|-------------|
| `uv run pytest` | Run all tests |
| `uv run ruff check .` | Lint |
| `uv run black .` | Format |
| `uv run mypy shared services tests` | Type-check |
| `make check` | All quality gates (Unix) |
| `docker compose up -d postgres` | Start local PostgreSQL |

## What is implemented in this phase

- Six independent FastAPI applications with health endpoints
- Clean-architecture folder layout per service
- Shared configuration via `shared/config.py`
- Infrastructure directory placeholders
- Sample pytest per service
- Updated `.gitignore` (`.env` is never committed)

## Intentionally not implemented yet

- Authentication, JWT, and RBAC
- Database models, SQLAlchemy, and Alembic migrations
- Dockerfiles and Kubernetes manifests
- Business logic, AI logic, and API Gateway routing

These arrive in subsequent phases.
