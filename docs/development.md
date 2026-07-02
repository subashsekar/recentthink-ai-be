# Local Development

This guide covers the day-to-day local workflow: environment setup, running
services, and the quality gates.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (manages Python 3.13 and dependencies)
- Docker (for PostgreSQL / the full stack)
- Optional: GNU Make (targets work on Linux/macOS and Git Bash/WSL; on native
  Windows PowerShell, run the underlying `uv` commands shown in each target)

## First-time setup

```bash
uv sync --all-groups     # create .venv and install everything (make install)
cp .env.example .env      # configure environment (copy on Windows)
```

uv installs the correct Python interpreter automatically. You rarely need to
activate the venv — prefix commands with `uv run`. To activate manually:

```bash
source .venv/bin/activate          # macOS / Linux
.venv\Scripts\Activate.ps1        # Windows PowerShell
```

## Configuration

Settings load from environment variables and `.env` via Pydantic
`BaseSettings` (`shared/config.py`). Supported environments: `local`,
`development`, `staging`, `production`, `test`.

**Security guard:** `local` and `test` may keep the default `SECRET_KEY` (a
warning is emitted). In any other environment the app **raises at startup** if
`SECRET_KEY` is still the insecure default — set a strong value before
deploying.

## Running services

Start a database first if a service needs one:

```bash
make db-up                # docker compose up -d postgres
```

Run any service with hot reload:

```bash
make run-gateway          # :8000
make run-auth             # :8001
make run-user             # :8002
make run-admin            # :8003
make run-ai               # :8004
make run-usage            # :8005
```

Each target is equivalent to:

```bash
cd services/<name> && uv run uvicorn app.main:app --reload --port <port>
```

Open `http://localhost:<port>/docs` for the interactive OpenAPI UI.

## Quality gates

| Task | Make target | Command |
|--------------|----------------|-------------------------------------------|
| Lint | `make lint` | `uv run ruff check .` |
| Format | `make format` | `uv run isort . && uv run black .` |
| Format check | `make format-check` | `uv run isort --check-only . && uv run black --check .` |
| Type check | `make typecheck` | `mypy shared tests` + per-service `mypy --explicit-package-bases app` |
| Test | `make test` | `uv run pytest` |
| Everything | `make check` | lint + format-check + typecheck + test |

### Why mypy runs per service

Every service roots its own `app` package, so a single `mypy services` run
cannot disambiguate six identically named packages. The `typecheck` target
therefore checks `shared` + `tests` centrally and then each service's `app`
from within its own directory (with `MYPYPATH=.` and `--explicit-package-bases`).
The `shared` package ships a `py.typed` marker so its types are honoured.

## Migrations & seeding

See [database.md](database.md). Quick reference:

```bash
make migrate              # upgrade head
make migrate-down         # downgrade -1
make seed-admin           # create default admin
```

## Coding conventions

- Python type hints everywhere; mypy runs in strict mode.
- PEP 8 enforced by Ruff + Black (line length 88); imports sorted by isort
  (Black profile).
- Keep business logic in `services/`, data access in `repositories/`, and HTTP
  concerns in `api/`.
- Import shared behaviour from `shared/` instead of duplicating it.
