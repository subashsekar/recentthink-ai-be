"""One-off scaffold helper for service layer __init__.py files."""

from __future__ import annotations

from pathlib import Path

SERVICES = [
    "gateway",
    "auth_service",
    "user_service",
    "admin_service",
    "ai_service",
    "usage_service",
]

LAYER_DOCS = {
    "api": "HTTP route handlers and API routers.",
    "core": "Service-specific configuration and core primitives.",
    "services": "Business logic and use-case orchestration.",
    "repositories": "Data access layer abstractions.",
    "models": "Domain and persistence models.",
    "schemas": "Request and response Pydantic schemas.",
    "dependencies": "FastAPI dependency injection providers.",
    "middleware": "HTTP middleware components.",
    "utils": "Service-specific utility functions.",
}

root = Path(__file__).resolve().parents[1] / "services"

for service_name in SERVICES:
    app = root / service_name / "app"
    for subdir, doc in LAYER_DOCS.items():
        init = app / subdir / "__init__.py"
        if subdir == "core" and (app / "core" / "config.py").exists():
            if not init.exists():
                init.write_text(f'"""{doc}"""\n', encoding="utf-8")
            continue
        init.parent.mkdir(parents=True, exist_ok=True)
        init.write_text(f'"""{doc}"""\n', encoding="utf-8")
    print(f"Scaffolded layers for {service_name}")
