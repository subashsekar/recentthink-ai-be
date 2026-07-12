# RecentThink AI Service

Production-ready reusable AI platform built on FastAPI, LangGraph, and OpenRouter.

Phase 6 adds **DSA Pattern Coach** as the fourth AI product on the shared platform. LeetCode Mentor, HackerRank Mentor, Learning Path Generator, and DSA Pattern Coach are thin adapters over the shared `AIWorkflowEngine` — exactly **one OpenRouter request** per generate/analyze.

## Architecture

```
User
  │
  ▼
Feature Adapter (LeetCode / HackerRank / Course Generator / DSA Pattern Coach)
  │
  ▼
Planner (deterministic — no LLM)
  │
  ▼
AIWorkflowEngine / OpenRouter (single structured JSON call)
  │
  ▼
Teacher → Coder → Code Explainer → Evaluator (format only — no LLM)
  │
  ▼
Conversation Memory → History → Execution Trace → Usage Tracker → Progress
  │
  ▼
Frontend
```

### DSA Pattern Coach Adapter

Location: `app/agents/dsa_pattern/`

Unlike LeetCode/HackerRank (problem-centric), this module is **pattern-centric**. The user provides only a DSA pattern name (e.g. Sliding Window) plus level, language, and learning style.

| Component | Responsibility |
|-----------|----------------|
| `schemas.py` | Generate/follow-up/progress/export API models |
| `adapter.py` | Maps platform `ChatResponse` → pattern schemas + export helpers |
| `service.py` | Thin orchestration — delegates to `AIPlatformService` |
| `router.py` | `/dsa-pattern/*` endpoints (mounted in `main.py`) |
| `agents.py` | Declarative specs (learning/recognition/visualization/… are logical, not extra LLM calls) |
| `catalog.py` | Example pattern cards |

DSA Pattern Coach does **not** implement its own workflow, memory, history, or usage tracking.

### Learning Workflow

1. Validate inputs (`pattern`, `level`, `language`, `learning_style`).
2. Pattern Planner builds category, difficulty, prerequisites, study time, objectives, roadmap (**0 LLM calls**).
3. **One** OpenRouter call returns `teacher` + `dsa_pattern` JSON.
4. Logical stages parsed from that JSON: Learning → Recognition → Visualization → Template → Walkthrough → Practice → Quiz.
5. Progress Coach updates `pattern_progress` / `pattern_mastery`.
6. Follow-ups reuse Conversation Memory (`Explain again`, `Generate another quiz`, `Compare patterns`, etc.).

### Recognition Strategy

The Recognition Agent teaches **how to identify** whether a problem belongs to the pattern:

- Keywords (e.g. Sliding Window → continuous, substring, subarray, window)
- Signals, recognition rules, decision tree
- Common clues + detection checklist

### Visualization

Frontend-friendly ASCII diagrams, pointer/step movement, array/graph/tree/stack/queue evolution — all plain text suitable for UI rendering.

## LangGraph Workflow

```
START → planner → openrouter → teacher → coder → code_explainer → evaluator → persist → END
```

| Node | Responsibility | LLM Calls |
|------|----------------|-----------|
| **Planner** | Validate input, classify request, select modules | 0 |
| **OpenRouter** | Single structured JSON completion | 1 |
| **Teacher** | Format teacher JSON → markdown + frontend cards | 0 |
| **Coder** | Format coder JSON → code blocks | 0 |
| **Code Explainer** | Explain code line-by-line from structured JSON | 0 |
| **Evaluator** | Format evaluator JSON → feedback | 0 |
| **Persist** | Update session, memory, usage | 0 |

For DSA Pattern Coach, planner selects only `TEACHER`. Learning/recognition/visualization/template/walkthrough/practice/quiz content is produced inside the single OpenRouter `dsa_pattern` object.

## Database Design

| Table | Purpose |
|-------|---------|
| `pattern_sessions` | Generated pattern lesson + JSONB sections |
| `pattern_progress` | Per-user aggregates (learned/mastered, streak, quiz scores) |
| `pattern_mastery` | Per-user per-pattern mastery status |
| `pattern_bookmarks` | Bookmarked recognition/examples/templates |
| `ai_sessions` / `ai_messages` / `conversation_memory` | Shared history + memory (reused) |

## API Endpoints

### Platform (`/ai/*`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/ai/chat` | JWT | Run the generic AI pipeline |
| POST | `/ai/follow-up` | JWT | Handle follow-up using session context |
| GET | `/ai/history` | JWT | List session history |
| GET | `/ai/models` | JWT | List configured LLM models |

### LeetCode (`/leetcode/*`) / HackerRank (`/hackerrank/*`) / Courses (`/courses/*`)

See product routers for analyze/generate, follow-up, history, progress, examples, export.

### DSA Pattern Coach (`/dsa-pattern/*`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/dsa-pattern/generate` | JWT | Generate full pattern lesson (1 OpenRouter call) |
| POST | `/dsa-pattern/follow-up` | JWT | Continue session (explain / more examples / quiz / compare) |
| GET | `/dsa-pattern/history` | JWT | List pattern sessions |
| GET | `/dsa-pattern/history/{session_id}` | JWT | Detail + messages |
| DELETE | `/dsa-pattern/history/{session_id}` | JWT | Delete pattern session + AI session |
| GET | `/dsa-pattern/progress` | JWT | Aggregate + mastery |
| POST | `/dsa-pattern/progress` | JWT | Update practice/quiz/mastery |
| GET | `/dsa-pattern/dashboard` | JWT | Progress + recent/active sessions |
| GET | `/dsa-pattern/examples` | JWT | Example pattern cards |
| POST | `/dsa-pattern/export/markdown` | JWT | Export as Markdown |
| POST | `/dsa-pattern/export/json` | JWT | Export as JSON |
| POST | `/dsa-pattern/export/pdf` | JWT | Export as PDF |

### Example generate request

```json
{
  "pattern": "Sliding Window",
  "level": "Beginner",
  "language": "Python",
  "learning_style": "Visual"
}
```

### Frontend response highlights

Pattern Overview, Mental Model, Recognition Guide, Visualization, Templates, Easy/Medium/Hard Examples, Interview Tips, Practice Problems, Quiz, Progress, Usage, Execution Trace.

## Security

- JWT authentication on all `/dsa-pattern/*` endpoints
- RBAC with owner validation on session access
- Prompt injection sanitization (shared workflow)
- Rate limits: generate `5/minute`, follow-up `20/minute`

## Directory Structure

```
app/
├── agents/
│   ├── leetcode/           # Problem mentor adapter
│   ├── hackerrank/         # Challenge mentor adapter
│   ├── course_generator/   # Learning Path Generator adapter
│   ├── dsa_pattern/        # DSA Pattern Coach adapter
│   └── shared/             # Workflow, planner, teacher, memory, follow-up
├── prompts/
│   ├── leetcode/v1/
│   ├── course_generator/v1/single_llm.txt
│   ├── dsa_pattern/v1/single_llm.txt
│   └── shared/v1/
└── main.py                 # Mounts /ai, /leetcode, /hackerrank, /courses, /dsa-pattern
```

## Running

```bash
make run-ai
# or
cd services/ai_service && uv run uvicorn app.main:app --reload --port 8004
```

## Migrations

```bash
uv run alembic upgrade head
```

- Phase 5: `l3g8b9c0d1e2_add_course_generator_tables`
- Phase 6: `m4h9c0d1e2f3_add_dsa_pattern_tables` (`pattern_sessions`, `pattern_progress`, `pattern_mastery`, `pattern_bookmarks`)

## Testing

```bash
cd services/ai_service
uv run pytest tests/test_dsa_pattern_api.py tests/test_dsa_pattern_adapter.py -q
```

## AI Products

- **LeetCode Mentor** — `agents/leetcode/`
- **HackerRank Mentor** — `agents/hackerrank/`
- **Learning Path Generator** — `agents/course_generator/`
- **DSA Pattern Coach** — `agents/dsa_pattern/` (flagship pattern-centric learning)
- **Interview Trainer** — scaffold for a future product
