# RecentThink developer commands.
# Usage: `make <target>`. On Windows use Git Bash / WSL, or run the underlying
# `uv` commands directly (see the README).

.DEFAULT_GOAL := help
.PHONY: help install sync \
	format format-check lint typecheck test coverage check \
	run-gateway run-auth run-user run-admin run-ai run-usage \
	migrate migrate-down migrate-history migrate-revision seed-admin \
	db-up db-down docker-build docker-up docker-down docker-logs clean

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
install: ## Create the venv and install all (incl. dev) dependencies
	uv sync --all-groups

sync: ## Sync the environment to match uv.lock exactly
	uv sync --all-groups --frozen

# ---------------------------------------------------------------------------
# Quality gates
# ---------------------------------------------------------------------------
format: ## Auto-format with isort + Black
	uv run isort .
	uv run black .

format-check: ## Check formatting without writing changes
	uv run isort --check-only .
	uv run black --check .

lint: ## Lint the codebase with Ruff
	uv run ruff check .

typecheck: ## Static type checking with mypy (shared + each service's app)
	uv run mypy shared tests
	@for svc in gateway auth_service user_service admin_service ai_service usage_service; do \
		echo "==> mypy services/$$svc/app"; \
		( cd services/$$svc && MYPYPATH=. uv run mypy --explicit-package-bases app ) || exit 1; \
	done

test: ## Run the full test suite (root + service + CRUD tests)
	uv run pytest

coverage: ## Run tests and produce term + HTML coverage reports
	uv run pytest --cov-report=term-missing --cov-report=html

check: lint format-check typecheck test ## Run all quality gates

# ---------------------------------------------------------------------------
# Run individual services (each on its assigned port)
# `app.main:app` resolves because the working directory is the service root;
# `shared` resolves via the editable project install.
# ---------------------------------------------------------------------------
run-gateway: ## Run the API Gateway on :8000
	cd services/gateway && uv run uvicorn app.main:app --reload --port 8000

run-auth: ## Run the Auth Service on :8001
	cd services/auth_service && uv run uvicorn app.main:app --reload --port 8001

run-user: ## Run the User Service on :8002
	cd services/user_service && uv run uvicorn app.main:app --reload --port 8002

run-admin: ## Run the Admin Service on :8003
	cd services/admin_service && uv run uvicorn app.main:app --reload --port 8003

run-ai: ## Run the AI Service on :8004
	cd services/ai_service && uv run uvicorn app.main:app --reload --port 8004

run-usage: ## Run the Usage Service on :8005
	cd services/usage_service && uv run uvicorn app.main:app --reload --port 8005

# ---------------------------------------------------------------------------
# Alembic migrations
# ---------------------------------------------------------------------------
migrate: ## Apply all migrations (alembic upgrade head)
	uv run alembic upgrade head

migrate-down: ## Roll back the most recent migration (alembic downgrade -1)
	uv run alembic downgrade -1

migrate-history: ## Show the migration history
	uv run alembic history --verbose

migrate-revision: ## Autogenerate a revision: make migrate-revision m="message"
	uv run alembic revision --autogenerate -m "$(m)"

seed-admin: ## Seed the default system administrator
	uv run python scripts/seed_admin.py

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------
db-up: ## Start only the PostgreSQL container
	docker compose up -d postgres

db-down: ## Stop and remove local infrastructure containers
	docker compose down

docker-build: ## Build all service images
	docker compose build

docker-up: ## Start the full stack (Postgres + all services)
	docker compose up -d

docker-down: ## Stop and remove the full stack
	docker compose down

docker-logs: ## Tail logs from all containers
	docker compose logs -f

clean: ## Remove caches and build artefacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage dist build
