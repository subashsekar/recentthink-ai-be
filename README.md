# RecentThink

A production-ready SaaS AI application built on a **microservice** + **clean
architecture** foundation. This repository currently contains only the project
foundation — no business logic, authentication, database models, or API
endpoints yet. It is structured to grow into AI agents and RAG workloads in
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

## Project structure

```
recentthink/
├── services/         # Individual microservices (added in later phases)
├── shared/           # Code shared across services (config, utils, etc.)
│   └── config.py     # Pydantic BaseSettings configuration
├── infrastructure/   # IaC / deployment / container assets (later phases)
├── docs/             # Project documentation
├── scripts/          # Developer & operational scripts
├── tests/            # Test suite
├── .github/workflows # CI pipelines
├── .env.example      # Sample environment configuration
├── pyproject.toml    # Project metadata, dependencies & tool config
├── docker-compose.yml# Local infrastructure (PostgreSQL)
├── Makefile          # Common developer commands
└── uv.lock           # Locked, reproducible dependency versions
```

## Getting started

### 1. Install uv

uv is the package and environment manager for this project.

**macOS / Linux:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Alternatively: `pip install uv` or `brew install uv`. Verify with `uv --version`.

### 2. Sync dependencies

This creates a virtual environment in `.venv/` and installs all dependencies
(including the `dev` group) exactly as pinned in `uv.lock`:

```bash
uv sync --all-groups
```

uv also installs the correct Python interpreter (3.13) automatically if needed.

### 3. Activate the environment

You usually don't need to activate it — prefix commands with `uv run`
(e.g. `uv run pytest`). To activate it manually:

**macOS / Linux:**

```bash
source .venv/bin/activate
```

**Windows (PowerShell):**

```powershell
.venv\Scripts\Activate.ps1
```

### 4. Configure environment variables

```bash
cp .env.example .env   # Windows: copy .env.example .env
```

## Common commands

You can use the `Makefile` (on macOS/Linux or Git Bash/WSL) or run the `uv`
commands directly (works everywhere, including Windows PowerShell).

### Run the tests

```bash
uv run pytest          # or: make test
```

### Run tests with coverage

```bash
uv run pytest --cov-report=html   # or: make coverage
```

An HTML report is written to `htmlcov/index.html`.

### Lint with Ruff

```bash
uv run ruff check .    # or: make lint
uv run ruff check --fix .
```

### Format with Black (and isort)

```bash
uv run isort .         # sort imports
uv run black .         # format code        (or: make format)
uv run black --check . # verify only        (or: make format-check)
```

### Type-check with mypy

```bash
uv run mypy shared services tests   # or: make typecheck
```

### Run everything (quality gates)

```bash
make check
```

### Local database

```bash
docker compose up -d postgres   # or: make db-up
docker compose down             # or: make db-down
```

## Notes for this phase

The following are intentionally **not** implemented yet and will arrive in
later phases:

- Authentication & business logic
- Database models
- Alembic migrations
- Dockerfiles for services
- API endpoints
- The microservices themselves
