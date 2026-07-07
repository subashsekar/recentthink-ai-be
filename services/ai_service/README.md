# RecentThink AI Service

Production-ready reusable AI platform built on FastAPI, LangGraph, and OpenRouter.

Phase 2.5 consolidates **LeetCode** as the reference implementation for all future AI products. LeetCode is a thin adapter over the shared `AIWorkflowEngine` — exactly **one OpenRouter request** per analyze.

## Architecture

```
User
  │
  ▼
LeetCode Adapter (validate URL, fetch problem, normalize context)
  │
  ▼
Planner (deterministic — no LLM)
  │
  ▼
AIWorkflowEngine / OpenRouter (single structured JSON call)
  │
  ▼
Teacher Module → Coder Module → Evaluator Module (format only — no LLM)
  │
  ▼
Conversation Memory → History → Execution Trace → Usage Tracker → Progress
  │
  ▼
Frontend
```

### LeetCode Adapter

Location: `app/agents/leetcode/`

| Component | Responsibility |
|-----------|----------------|
| `problem_fetcher.py` | LeetCode GraphQL fetch + manual input |
| `adapter.py` | Maps platform `ChatResponse` → LeetCode API schemas |
| `service.py` | Thin orchestration — delegates to `AIPlatformService` |
| `router.py` | `/leetcode/*` endpoints (mounted in `main.py`) |

LeetCode does **not** implement its own agents, prompts, memory, history, or usage tracking.

### Follow-up Flow (LeetCode)

```
POST /leetcode/follow-up  (or POST /ai/follow-up)
  │
  ├── Load session memory (planner + teacher context)
  ├── FollowUpEngine (classify intent)
  ├── OpenRouter (targeted follow-up prompt)
  ├── TeacherModule (format response)
  └── Update conversation memory
```

## LangGraph Workflow

```
START → planner → openrouter → teacher → coder → evaluator → persist → END
```

| Node | Responsibility | LLM Calls |
|------|----------------|-----------|
| **Planner** | Validate input, classify request, select modules | 0 |
| **OpenRouter** | Single structured JSON completion | 1 |
| **Teacher** | Format teacher JSON → markdown + frontend cards | 0 |
| **Coder** | Format coder JSON → code blocks | 0 |
| **Evaluator** | Format evaluator JSON → feedback | 0 |
| **Persist** | Update session, memory, usage | 0 |

## Teacher Module

Location: `app/agents/shared/teacher/`

The Teacher Module reads structured JSON from OpenRouter and **never calls OpenRouter itself**. It behaves like a mentor — guiding learners without immediately revealing complete solutions.

### Output Fields

| Field | Description |
|-------|-------------|
| `problem_summary` | High-level problem overview |
| `thinking_process` | Step-by-step reasoning guidance |
| `learning_objectives` | What the learner should take away |
| `concepts` | DSA concepts involved |
| `approach` | Strategic approach (not full solution) |
| `common_mistakes` | Beginner pitfalls to avoid |
| `analogy` | Real-world analogy |
| `next_step` | Recommended next action for the learner |

### Example Structured Output

```json
{
  "problem_summary": "Find two numbers that add up to a target.",
  "thinking_process": "Consider what you need at each step...",
  "concepts": ["Hash Map"],
  "approach": "Store complements as you iterate.",
  "common_mistakes": ["Nested loops"],
  "analogy": "Like finding a matching sock in a laundry basket.",
  "next_step": "Think about storing previous values."
}
```

The `TeacherFormatter` produces both **markdown** (for chat display) and **frontend cards** (for structured UI).

## Conversation Memory

Location: `app/agents/shared/memory/` and `app/services/memory/`

### Memory Strategy

| Layer | Storage | Purpose |
|-------|---------|---------|
| **Recent Memory** | `recent_messages` (JSONB) | Last N exchanges for follow-up context |
| **Long-Term Memory** | `previous_responses` (JSONB) | Historical assistant responses |
| **Conversation Summary** | `summary` (text) | Compressed context for token optimization |

When conversations grow large, the summarizer (`POST /ai/session/{id}/summarize`) generates a summary, stores it, and the `ContextPruner` reduces token usage by trimming recent messages and context.

### Database: `conversation_memory`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `session_id` | UUID | FK to `ai_sessions` (unique) |
| `user_id` | UUID | Owner for isolation |
| `summary` | text | Conversation summary |
| `context` | JSONB | Planner output, teacher output, problem context |
| `recent_messages` | JSONB | Recent user/assistant exchanges |
| `previous_responses` | JSONB | Long-term response history |
| `follow_up_questions` | JSONB | Suggested follow-ups |
| `memory_version` | int | Schema version for future migrations |
| `created_at` / `updated_at` | timestamp | Audit fields |

## Follow-up Engine

Location: `app/agents/shared/followup/`

Recognizes intents such as:

- Explain again / easier / visually
- Give another example
- Simplify / edge cases
- "I didn't understand"

Reuses existing planner and teacher context — does not regenerate unrelated content.

## Prompt Management

Location: `app/prompts/`

| Path | Purpose |
|------|---------|
| `leetcode/v1/single_llm.txt` | LeetCode single-LLM orchestration (OpenRouter) |
| `leetcode/v1/planner.md` | Deterministic planner documentation |
| `leetcode/v1/teacher.md` | Teacher module formatting reference |
| `leetcode/v1/coder.md` | Coder module formatting reference |
| `leetcode/v1/evaluator.md` | Evaluator module formatting reference |
| `teacher/v1/system.md` | Mentor behavior and follow-up JSON schema |
| `teacher/v1/followup.md` | Follow-up question handling |
| `shared/v1/single_llm.txt` | Generic fallback orchestration prompt |

Prompts support versioning via `PromptLoader` (filesystem + DB overrides + hot reload). Never hardcode prompts in code.

## API Endpoints

### Platform (`/ai/*`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/ai/chat` | JWT | Run the generic AI pipeline |
| POST | `/ai/follow-up` | JWT | Handle follow-up using session context |
| POST | `/ai/session/{id}/summarize` | JWT | Generate conversation summary |
| DELETE | `/ai/memory/{session_id}` | JWT | Clear conversation memory |
| GET | `/ai/history` | JWT | List session history |
| GET | `/ai/history/{session_id}` | JWT | Session detail with memory + teacher responses |
| DELETE | `/ai/history/{session_id}` | JWT | Delete a session |
| GET | `/ai/models` | JWT | List configured LLM models |

### LeetCode (`/leetcode/*`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/leetcode/analyze` | JWT | Fetch problem + run single-LLM workflow |
| POST | `/leetcode/follow-up` | JWT | Follow-up in existing LeetCode session |
| GET | `/leetcode/history` | JWT | LeetCode session history |
| GET | `/leetcode/history/{session_id}` | JWT | Session detail with messages |
| DELETE | `/leetcode/history/{session_id}` | JWT | Delete session |
| GET | `/leetcode/progress` | JWT | Practice progress stats |

### GET `/ai/history/{session_id}` Response

Returns session metadata, messages, conversation memory snapshot, teacher responses, and follow-up messages.

## Session Continuation

Pass the same `session_id` on `POST /ai/chat` or use `POST /ai/follow-up` for targeted questions:

- "Explain again"
- "Give another example"
- "I didn't understand"
- "What about edge cases?"

Memory loads planner and teacher output from prior turns, avoiding full replanning when possible.

## Security

- JWT authentication on all `/ai/*` endpoints
- RBAC with admin override for history access
- Owner validation on session and memory operations
- Memory isolation between users
- Prompt injection sanitization
- API keys and JWTs never logged

## Usage Tracking

Tracks follow-up requests, memory retrieval, token usage, execution time, latency, and estimated cost via `UsageTracker` → Usage Service + `model_usage` table.

## Directory Structure

```
app/
├── agents/
│   ├── leetcode/           # Reference adapter (fetch, map, progress)
│   └── shared/
│       ├── teacher/        # Formatter, schemas, module
│       ├── memory/         # Engine, pruner, summarizer
│       ├── followup/       # Intent classification engine
│       ├── planner/        # Deterministic request planner
│       ├── workflow/       # LangGraph engine + nodes
│       └── orchestrator/   # Platform orchestrator
├── prompts/
│   ├── leetcode/v1/        # LeetCode prompts (single_llm + module docs)
│   ├── teacher/v1/         # Teacher prompts (system, followup, analogy, summary)
│   └── shared/v1/          # Single-LLM orchestration prompt
├── services/
│   ├── memory/             # ConversationMemoryService
│   ├── followup/           # FollowUpService
│   ├── history/            # HistoryManager
│   └── usage/              # UsageTracker
├── api/ai.py               # Platform HTTP routes
└── main.py                 # Mounts /ai and /leetcode routers
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

Sprint 3 adds `g9b4c5d6e7f8_extend_conversation_memory` (summary, recent_messages, memory_version).

## Testing

```bash
cd services/ai_service
uv run pytest tests/ -q --cov=app --cov-config=.coveragerc \
  --override-ini="addopts=-ra --strict-markers --strict-config --import-mode=importlib"
```

Platform coverage target: **>90%**.

## Future AI Products

Each product adds feature-specific logic under `agents/{feature}/` and automatically inherits the shared workflow, memory, follow-up, history, usage, and execution trace:

- **LeetCode Mentor** — reference implementation (`agents/leetcode/`)
- **HackerRank Mentor** — challenge fetcher adapter
- **DSA Tutor** — curriculum-aware teaching
- **Interview Trainer** — mock interview flows
- **Course Generator** — syllabus generation

Legacy `leetcode_sessions`, `chat_messages`, and `agent_runs` tables were removed in migration `h9c4d5e6f7a8`. All sessions use `ai_sessions`, `ai_messages`, and `agent_execution`.
