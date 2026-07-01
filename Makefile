# RecentThink developer commands.
# Usage: `make <target>`. On Windows use Git Bash / WSL, or run the underlying
# `uv` commands directly (see the README).

.DEFAULT_GOAL := help
.PHONY: help install sync lint format format-check typecheck test coverage check clean db-up db-down
.PHONY: run-gateway run-auth run-user run-admin run-ai run-usage migrate seed-admin

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Create the venv and install all (incl. dev) dependencies
	uv sync --all-groups

sync: ## Sync the environment to match uv.lock exactly
	uv sync --all-groups --frozen

run-gateway: ## Run the API Gateway on port 8000
	cd services/gateway && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

run-auth: ## Run the Auth Service on port 8001
	cd services/auth_service && uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

run-user: ## Run the User Service on port 8002
	cd services/user_service && uv run uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

run-admin: ## Run the Admin Service on port 8003
	cd services/admin_service && uv run uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload

run-ai: ## Run the AI Service on port 8004
	cd services/ai_service && uv run uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload

run-usage: ## Run the Usage Service on port 8005
	cd services/usage_service && uv run uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload

lint: ## Lint the codebase with Ruff
	uv run ruff check .

format: ## Auto-format with isort + Black
	uv run isort .
	uv run black .

format-check: ## Check formatting without writing changes
	uv run isort --check-only .
	uv run black --check .

typecheck: ## Static type checking with mypy
	uv run mypy shared services tests

test: ## Run the test suite
	uv run pytest

coverage: ## Run tests and produce a coverage report
	uv run pytest --cov-report=term-missing --cov-report=html

check: lint format-check typecheck test ## Run all quality gates

db-up: ## Start the local PostgreSQL container
	docker compose --profile local-db up -d postgres

db-down: ## Stop and remove local infrastructure containers
	docker compose --profile local-db down

migrate: ## Apply database migrations (Alembic upgrade head)
	uv run alembic upgrade head

seed-admin: ## Seed the default system administrator account
	uv run python scripts/seed_admin.py

clean: ## Remove caches and build artefacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage dist build
