# RecentThink developer commands.
# Usage: `make <target>`. On Windows use Git Bash / WSL, or run the underlying
# `uv` commands directly (see the README).

.DEFAULT_GOAL := help
.PHONY: help install sync run lint format format-check typecheck test coverage check clean db-up db-down

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Create the venv and install all (incl. dev) dependencies
	uv sync --all-groups

sync: ## Sync the environment to match uv.lock exactly
	uv sync --all-groups --frozen

run: ## Run the (placeholder) ASGI app with hot reload
	uv run uvicorn shared.config:settings --reload

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
	docker compose up -d postgres

db-down: ## Stop and remove local infrastructure containers
	docker compose down

clean: ## Remove caches and build artefacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage dist build
