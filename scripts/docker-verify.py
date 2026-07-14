#!/usr/bin/env python3
"""Verify the RecentThink Docker Compose stack is healthy and print service URLs."""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request

GATEWAY_URL = "http://localhost:8000/"
POSTGRES_HOST_PORT = "localhost:5432"

INTERNAL_SERVICES = (
    ("auth_service", "http://auth_service:8001/"),
    ("user_service", "http://user_service:8002/"),
    ("admin_service", "http://admin_service:8003/"),
    ("ai_service", "http://ai_service:8004/"),
    ("usage_service", "http://usage_service:8005/"),
)


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def _compose_ps(*, all_containers: bool = False) -> dict[str, str]:
    cmd = ["docker", "compose", "ps", "--format", "json"]
    if all_containers:
        cmd.insert(3, "-a")
    result = _run(cmd)
    if result.returncode != 0:
        print(result.stderr or result.stdout, file=sys.stderr)
        raise SystemExit(1)

    statuses: dict[str, str] = {}
    raw = result.stdout.strip()
    if not raw:
        return statuses

    # Compose may emit one JSON object per line or a JSON array.
    if raw.startswith("["):
        rows = json.loads(raw)
    else:
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]

    for row in rows:
        name = row.get("Service") or row.get("Name") or ""
        health = row.get("Health") or ""
        state = row.get("State") or row.get("Status") or ""
        exit_code = row.get("ExitCode")
        label = health or state
        if exit_code not in (None, "", 0, "0") and not health:
            label = f"{state} (exit {exit_code})"
        elif state and "exited" in str(state).lower() and exit_code in (0, "0", None, ""):
            label = "exited(0)"
        statuses[name] = label
    return statuses


def _http_ok(url: str, timeout: float = 5.0) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status == 200, body
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, str(exc)


def _internal_health(service: str, url: str) -> tuple[bool, str]:
    script = (
        "import urllib.request; "
        f"r = urllib.request.urlopen('{url}', timeout=5); "
        "print(r.read().decode())"
    )
    result = _run(
        ["docker", "compose", "exec", "-T", "gateway", "python", "-c", script],
    )
    if result.returncode != 0:
        return False, (result.stderr or result.stdout).strip()
    return True, result.stdout.strip()


def main() -> None:
    print("Checking Docker Compose service health...")
    statuses = _compose_ps(all_containers=True)
    expected = [
        "postgres",
        "migrate",
        "auth_service",
        "user_service",
        "usage_service",
        "ai_service",
        "admin_service",
        "gateway",
    ]

    failed = False
    for name in expected:
        state = statuses.get(name, "missing")
        if name == "migrate":
            ok = "exited(0)" in state.lower() or state.lower() in {
                "exited",
                "healthy",
            }
            marker = "OK" if ok else "FAIL"
            print(f"  [{marker}] migrate: {state}")
            if not ok:
                failed = True
            continue
        healthy = "healthy" in state.lower()
        marker = "OK" if healthy else "FAIL"
        print(f"  [{marker}] {name}: {state}")
        if not healthy:
            failed = True

    print("\nProbing Gateway (host)...")
    ok, body = _http_ok(GATEWAY_URL)
    print(f"  [{'OK' if ok else 'FAIL'}] GET {GATEWAY_URL} -> {body[:120]}")
    if not ok:
        failed = True

    print("\nProbing internal services via gateway container...")
    for service, url in INTERNAL_SERVICES:
        ok, body = _internal_health(service, url)
        print(f"  [{'OK' if ok else 'FAIL'}] {service}: {body[:120]}")
        if not ok:
            failed = True

    print("\nService URLs")
    print("------------")
    print(f"  Gateway (public):     http://localhost:8000")
    print(f"  Gateway docs:         http://localhost:8000/docs")
    print(f"  PostgreSQL (public):  postgresql://recentthink:***@{POSTGRES_HOST_PORT}/recentthink")
    print("  Auth (internal):      http://auth_service:8001")
    print("  User (internal):      http://user_service:8002")
    print("  Admin (internal):     http://admin_service:8003")
    print("  AI (internal):        http://ai_service:8004")
    print("  Usage (internal):     http://usage_service:8005")
    print("  Network:              recentthink-network")

    if failed:
        print("\nStack verification FAILED.", file=sys.stderr)
        raise SystemExit(1)
    print("\nStack verification PASSED.")


if __name__ == "__main__":
    main()
