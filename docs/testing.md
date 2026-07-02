# Testing

Tests use **pytest** with `pytest-asyncio` and `pytest-cov`. Configuration
lives in `pyproject.toml` under `[tool.pytest.ini_options]`.

## Test layout

| Location | Kind | Needs DB? |
|----------------------------------|--------------------------------------|-----------|
| `tests/test_config.py` | Shared settings unit tests | No |
| `services/<name>/tests/` | Per-service health/endpoint tests | No |
| `tests/crud/` | User/Admin repository integration | **Yes** |

`testpaths = ["tests", "services"]` so a single `pytest` run discovers the root
suite, the CRUD tests, and every service's own tests.

### Import mode

Because multiple services contain identically named modules (e.g. several
`test_health.py` and `conftest.py`), pytest runs with
`--import-mode=importlib`. This lets same-named test modules coexist without
`__init__.py` files. Service test isolation (swapping the `app` package on
`sys.path` per service) is handled by `services/conftest.py` together with each
service's `tests/conftest.py`.

## Running tests

```bash
make test                     # uv run pytest  (all tests)
make coverage                 # + HTML report at htmlcov/index.html
uv run pytest -m "not db"     # skip database-backed tests
uv run pytest services/gateway/tests   # a single service
```

## Database-backed tests

CRUD integration tests are marked with `@pytest.mark.db` (registered in
`pyproject.toml`). They require a live PostgreSQL and the schema to exist.

```bash
make db-up                    # start Postgres
uv run alembic upgrade head   # create tables
uv run pytest                 # run everything, including db tests
```

Each CRUD test runs inside a transaction that is rolled back on teardown
(`tests/crud/conftest.py`), so the database is left clean between tests.

Without a database, run `uv run pytest -m "not db"` to execute the rest of the
suite.

## Coverage

Coverage is configured for `shared` and `services` with branch coverage and a
`term-missing` + HTML report. Reports are written to `htmlcov/`.

## Continuous integration

`.github/workflows/ci.yml` runs on every push/PR to `main`:

1. `uv sync --all-groups --frozen`
2. Ruff, isort (check), Black (check)
3. mypy — `shared` + `tests`, then each service's `app`
4. `alembic upgrade head` against a PostgreSQL **service container**
5. `pytest` (all tests, including `db`-marked CRUD tests) with coverage

The Postgres service container exposes `localhost:5432`, and `DATABASE_URL` is
provided to the job so migrations and CRUD tests run against it.
