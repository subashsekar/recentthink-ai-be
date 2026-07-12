# How to Start RecentThink

Frontend talks only to the **Gateway** (`http://localhost:8000`).  
Gateway proxies to Auth, AI, Usage, and other services — those must also be running.

---

## Option A — One command (Docker)

Starts Postgres + Gateway + Auth + User + Admin + AI + Usage.

```bash
# From repo root: recentthink-ai-be
# Ensure .env exists (create from your team template if needed)

make docker-up
# same as: docker compose up -d
```

| Check | URL |
|-------|-----|
| Gateway liveness | http://localhost:8000/ |
| Gateway readiness (all services) | http://localhost:8000/health |
| Gateway docs | http://localhost:8000/docs |
| Auth (direct) | http://localhost:8001/docs |

Stop:

```bash
make docker-down
```

Logs:

```bash
make docker-logs
```

Then start the frontend (separate repo):

```bash
cd ~/recentthink-ai-fe
npm run dev
# → http://localhost:3000 (or :3001 if 3000 is busy)
```

Frontend `.env` should include:

```env
NEXT_PUBLIC_GATEWAY_URL=http://localhost:8000
```

Gateway CORS must include your frontend origin. Defaults include `:3000` and `:3001`; if `.env` sets `CORS_ORIGINS`, add the port you use, e.g.:

```env
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001
```

---

## Option B — Local (uv / separate terminals)

### First-time setup (once)

```bash
# From repo root: recentthink-ai-be
uv sync --all-groups
# Ensure .env exists with DATABASE_URL and secrets

# Start Postgres (Docker) if you are not using an existing local DB
make db-up             # or: docker compose up -d postgres

# Apply migrations + seed admin (when needed)
make migrate
make seed-admin
```

### Start services

**Minimum for login + LeetCode** — 3 terminals:

```bash
# Terminal 1 — Gateway :8000
cd services/gateway
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2 — Auth :8001
cd services/auth_service
uv run uvicorn app.main:app --reload --port 8001

# Terminal 3 — AI :8004
cd services/ai_service
uv run uvicorn app.main:app --reload --port 8004
```

Or from repo root with Make:

```bash
make run-gateway   # :8000
make run-auth      # :8001
make run-ai        # :8004
```

**Optional** (if the app needs them):

```bash
make run-usage     # :8005
make run-user      # :8002
make run-admin     # :8003
```

### Frontend

```bash
cd ~/recentthink-ai-fe
npm run dev
```

Open:

- Home: http://localhost:3000  
- Login: http://localhost:3000/login  
- Register: http://localhost:3000/register  

---

## Ports

| Service        | Port | Start from              |
|----------------|------|-------------------------|
| Gateway        | 8000 | `services/gateway`      |
| Auth           | 8001 | `services/auth_service` |
| User           | 8002 | `services/user_service` |
| Admin          | 8003 | `services/admin_service`|
| AI             | 8004 | `services/ai_service`   |
| Usage          | 8005 | `services/usage_service`|
| Frontend       | 3000 / 3001 | `recentthink-ai-fe` |
| Postgres (Docker host) | 5433 → 5432 | `docker compose` |

---

## Quick checks

```bash
# Gateway up?
curl http://localhost:8000/

# Auth reachable through Gateway? (expect 401/422 if body empty — not 502)
curl -i -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"you@example.com\",\"password\":\"secret\"}"
```

| Response | Meaning |
|----------|---------|
| **502** | Gateway up, Auth (or other upstream) not running |
| **401 / 422** | Gateway → Auth path works |
| **200** | Login succeeded |

---

## Common mistakes

1. Running only Gateway → login returns **502** (Auth must run on **8001**).  
2. Starting Gateway on port **8001** instead of Auth.  
3. Opening `http://localhost:3000/auth/login` as a page → use `/login` (pages) not `/auth/login` (API).  
4. Frontend `NEXT_PUBLIC_GATEWAY_URL` not pointing at `http://localhost:8000`.
