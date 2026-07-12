# AI Service — Concepts to Learn

A complete learning roadmap for understanding and building on the `ai_service` agents, workflow, and LLM pipeline in RecentThink.

Use this document as a study guide. Each section lists **what to learn**, **why it matters in this codebase**, and **where to look in the repo**.

---

## Table of Contents

1. [Mental Model First](#1-mental-model-first)
2. [Core Architecture Concepts](#2-core-architecture-concepts)
3. [Python & Backend Concepts](#3-python--backend-concepts)
4. [FastAPI & HTTP Layer](#4-fastapi--http-layer)
5. [AI / LLM Concepts](#5-ai--llm-concepts)
6. [Agent & Workflow Concepts](#6-agent--workflow-concepts)
7. [Prompt Engineering Concepts](#7-prompt-engineering-concepts)
8. [Data & Persistence Concepts](#8-data--persistence-concepts)
9. [Cross-Cutting Platform Concepts](#9-cross-cutting-platform-concepts)
10. [LeetCode Agent (Reference Implementation)](#10-leetcode-agent-reference-implementation)
11. [Concept Map (How Everything Connects)](#11-concept-map-how-everything-connects)
12. [Learning Path (Step-by-Step)](#12-learning-path-step-by-step)
13. [Skills Checklist](#13-skills-checklist)
14. [Glossary](#14-glossary)
15. [Key Files Index](#15-key-files-index)

---

## 1. Mental Model First

Before diving into files, internalize these three ideas:

### 1.1 Single-LLM Pipeline

The main workflow makes **exactly one LLM call** per analyze/chat request. That call returns a single JSON object with `teacher`, `coder`, and `evaluator` sections. Everything after that is **deterministic formatting** — no more LLM calls.

```
Request → Planner (no LLM) → OpenRouter (1 LLM call) → Teacher → Coder → Evaluator → Persist
```

### 1.2 "Agents" Are Not All LLM Agents

In this codebase, "agent" means different things:

| Type | Example | Calls LLM? |
|------|---------|------------|
| Processing module | `TeacherModule`, `CoderModule` | No — formats JSON |
| Deterministic planner | `Planner` | No — picks modules, builds metadata |
| Product adapter | `LeetCodeService` | No — prepares context, delegates |
| LLM gateway node | `openrouter_node` | **Yes — the only call in main flow** |
| Declarative spec | `LeetCodeAgentSpec` | No — metadata/documentation |

### 1.3 Thin Adapter Pattern

Product-specific code (LeetCode, HackerRank, etc.) should be **thin**:

1. Fetch or prepare domain data
2. Build a generic `ChatRequest`
3. Call `AIPlatformService.chat()`
4. Map `ChatResponse` back to product-specific shape

The shared pipeline does the real AI work.

---

## 2. Core Architecture Concepts

Learn these architectural patterns — they appear throughout the service.

### 2.1 Clean / Layered Architecture

Each request flows through distinct layers:

```
HTTP (api/) → Use-case (services/) → Orchestration (workflow/) → Infrastructure (clients/, repositories/)
```

| Layer | Responsibility | Example files |
|-------|----------------|---------------|
| Delivery | Routes, auth, validation | `app/api/ai.py`, `app/agents/leetcode/router.py` |
| Use-case | Business rules, session access | `app/services/ai_platform_service.py` |
| Orchestration | Pipeline coordination | `app/agents/shared/orchestrator/`, `workflow/graph.py` |
| Domain processing | Plan, format, validate | `planner/`, `teacher/`, `coder/`, `evaluator/` |
| Infrastructure | LLM, DB, external APIs | `clients/openrouter.py`, `repositories/` |

**Learn:** separation of concerns, dependency inversion, keeping framework code at the edges.

**Read:** `docs/architecture.md`

### 2.2 Dependency Injection (DI)

FastAPI's `Depends()` wires objects per request. All services are composed in one place:

- `app/dependencies/services.py` — builds `AIPlatformService` with repos, LLM client, orchestrator, etc.

**Learn:**
- Constructor injection
- Factory functions (`get_ai_platform_service`)
- Why manual `new OpenRouterClient()` inside routes is avoided

### 2.3 Repository Pattern

Database access is isolated in `repositories/`. Services never write raw SQL in route handlers.

Key repos:
- `AISessionRepository` — sessions
- `AIMessageRepository` — chat messages
- `ConversationMemoryRepository` — multi-turn context
- `AgentExecutionRepository` — execution traces

**Learn:** CRUD abstraction, testability with mocked repos.

### 2.4 Schema-Driven Design (Pydantic)

Every API input/output and LLM JSON shape is a Pydantic model:

- `ChatRequest`, `ChatResponse` — API contracts
- `UnifiedLLMResponse` — LLM output validation
- `PlannerOutput` — planner result
- `AIWorkflowState` — LangGraph state

**Learn:** validation, serialization, `model_copy()`, `model_dump()`, TypedDict vs BaseModel.

---

## 3. Python & Backend Concepts

### 3.1 Modern Python (3.11+)

Used throughout the codebase:

| Concept | Where used |
|---------|------------|
| `from __future__ import annotations` | Most modules — forward refs |
| `StrEnum` | `app/models/enums.py` — `AIFeature`, `ModuleName` |
| Type hints (`UUID`, `dict[str, Any]`) | Everywhere |
| `dataclass` | `LeetCodeAgentSpec`, `LLMResponse` |
| `AsyncIterator` | SSE streaming in LeetCode |
| `pathlib.Path` | Prompt file resolution |

### 3.2 Async / Await

The LLM client and workflow are async:

- `async def chat()` in routes and services
- `await self._llm.chat_completion()`
- `await self._graph.ainvoke()` in LangGraph

**Learn:** when to use async vs sync, `httpx.AsyncClient`, not blocking the event loop.

### 3.3 Error Handling

Custom exceptions from `shared.exceptions`:
- `ValidationException` — bad input
- `ForbiddenError` — session access denied
- `RecordNotFoundError` — missing session

**Learn:** fail fast in planner, partial vs failed workflow status, JSON retry on invalid LLM output.

---

## 4. FastAPI & HTTP Layer

### 4.1 FastAPI Fundamentals

| Concept | In this service |
|---------|-----------------|
| `APIRouter` | `/ai` and `/leetcode` routers |
| `Depends()` | Auth, DB session, service injection |
| `response_model` | Pydantic response validation |
| Lifespan | Sentry init in `main.py` |
| Middleware | CORS, `RequestIdMiddleware` |
| Rate limiting | `@limiter.limit()` on `/ai/chat` |

### 4.2 Authentication

- JWT bearer token → `AuthenticatedUser`
- `can_access_session()` — owner or admin only
- `app/dependencies/auth.py`

**Learn:** how the gateway forwards auth, how session ownership is enforced.

### 4.3 Server-Sent Events (SSE)

LeetCode supports streaming via `analyze_stream()`:
- Streams problem statement first
- Then full analysis result
- `app/utils/sse.py` — `format_sse_event()`

**Learn:** SSE vs WebSockets, `AsyncIterator[str]` as response.

### 4.4 Gateway Proxy

External clients often hit `services/gateway` which proxies to ai_service:
- `services/gateway/app/api/ai_proxy.py`

**Learn:** microservice routing, service-to-service HTTP.

---

## 5. AI / LLM Concepts

### 5.1 OpenRouter

OpenRouter is an API gateway to many LLM providers (OpenAI-compatible).

**Learn:**
- Chat completions API (`/chat/completions`)
- Model IDs like `anthropic/claude-3.5-sonnet`
- API key, base URL, timeout configuration (`.env`)
- Provider parsing (`anthropic` from `anthropic/claude-...`)

**File:** `app/clients/openrouter.py`

### 5.2 Structured Output (JSON Mode)

The service forces JSON responses:

- `response_format: { "type": "json_object" }`
- System prompt defines exact JSON schema
- `JSONValidator` validates against `UnifiedLLMResponse` Pydantic model
- Retries if JSON is invalid or empty

**Learn:** why structured output beats free-form text for pipelines, schema design, validation retry loops.

**Files:**
- `app/services/json_validator.py`
- `app/schemas/llm_response.py`
- `app/prompts/*/single_llm.txt`

### 5.3 Prompt Composition

At LLM call time, two prompts are merged:

```
system_prompt = coaching_mode_prompt + json_schema_prompt
user_prompt   = user message + problem context + memory
```

**Learn:** system vs user messages, context injection, prompt layering.

### 5.4 Model Registry

Models are configured in `app/config/models.json` and resolved via `ModelRegistry`:
- List available models
- Validate user-selected model
- Fallback to session or default model

**Learn:** model selection UX, per-model cost/latency tradeoffs.

### 5.5 Token Usage & Cost

Every LLM call tracks:
- `input_tokens`, `output_tokens`, `total_tokens`
- `latency_ms`
- `estimated_cost_usd` / `estimated_cost_inr`

**Files:** `app/utils/cost_calculator.py`, `app/services/usage/usage_tracker.py`

**Learn:** token counting, cost estimation, usage metering for billing.

### 5.6 Retry & Resilience

OpenRouter client retries on:
- HTTP 408, 429, 500, 502, 503, 504
- Exponential backoff
- Model fallback chain (primary → fallback model)

**Learn:** transient failure handling, idempotency considerations.

---

## 6. Agent & Workflow Concepts

### 6.1 LangGraph

The workflow engine uses **LangGraph** (`langgraph` package):

- `StateGraph(AIWorkflowState)` — graph of nodes
- Nodes are async functions: `async def planner_node(state) -> dict`
- Edges define execution order
- `MemorySaver` checkpointer for state
- `ainvoke()` runs the full pipeline

**File:** `app/agents/shared/workflow/graph.py`

**Learn:**
- State machines for AI pipelines
- Passing state between steps
- Why graphs beat giant if/else chains for multi-step AI

### 6.2 Workflow Nodes

| Node | Purpose | LLM? |
|------|---------|------|
| `planner` | Validate, classify, create session, load memory | No |
| `openrouter` | Compose prompts, call LLM, validate JSON | **Yes** |
| `teacher` | Format teacher JSON → markdown + cards | No |
| `coder` | Format code solutions | No |
| `evaluator` | Format complexity, feedback, follow-ups | No |
| `persist` | Save session, usage, memory, trace | No |

**File:** `app/agents/shared/workflow/nodes.py`

### 6.3 Planner (Deterministic)

The planner does **not** call an LLM. It:

1. Validates the request (non-empty message, max length)
2. Resolves `AIFeature` → list of modules to run
3. Builds metadata (patterns, execution plan, difficulty hints)
4. Respects coaching mode settings from `ModeRegistry`

**File:** `app/agents/shared/planner/planner.py`

**Learn:** when to use rules vs LLM for routing/classification.

### 6.4 Processing Modules

Each module implements:

```python
def process(
    self,
    *,
    session_id: UUID,
    payload: dict[str, Any],
    message_repo: AIMessageRepository | None = None,
) -> ModuleResponse:
```

Modules:
- Parse structured JSON payload
- Format to markdown / cards
- Persist assistant message to DB
- Return `ModuleResponse`

**Learn:** formatter pattern, separating generation from presentation.

### 6.5 Execution Trace

Every node execution is logged to `agent_executions` table:
- Module name, status, latency, tokens, errors
- `app/services/execution_trace.py`

**Learn:** observability, debugging AI pipelines.

### 6.6 Follow-Up Flow (Separate LLM Call)

Follow-up questions (`/ai/follow-up`, `/leetcode/follow-up`) use a **different path**:
- `FollowUpService` → `FollowUpEngine` classifies intent
- Separate OpenRouter call (teacher-only JSON)
- Updates conversation memory

**Learn:** when to break out of the main pipeline for a different use case.

---

## 7. Prompt Engineering Concepts

### 7.1 Two Prompt Systems

| System | Location | Purpose |
|--------|----------|---------|
| Feature prompts | `app/prompts/` | JSON output schema per feature |
| Coaching prompts | `app/coaching/prompts/` | Personality / teaching style |

### 7.2 Prompt Loading

`PromptLoader` resolves files with fallback chain:

```
prompts/{feature}/v1/{module}.txt
prompts/shared/v1/{module}.txt   ← fallback
```

Also supports:
- Versioning (`v1`, `v2`)
- Locale (`en`)
- DB overrides via `PromptVersionRepository`
- Hot reload in development

**File:** `app/services/prompt_loader.py`

### 7.3 Coaching Modes

Modes are configured in `app/config/coaching_modes.json`:

| Mode | Style | Temperature | Reveal answer? |
|------|-------|-------------|----------------|
| `learning` | Beginner, step-by-step | 0.7 | Yes |
| `teacher` | Lesson with checkpoints | 0.55 | Yes |
| `interview` | Concise, interviewer | 0.3 | No |
| `quick` | Fast, solution-first | 0.2 | Yes |

Each mode controls:
- `generation` — temperature, max_tokens, top_p
- `planner` — detail level, examples
- `teacher` — hints, reveal_answer, style
- `evaluator` — strictness, verbosity
- `analyze_prompt` — which coaching txt file to load

**Files:** `app/coaching/registry.py`, `app/config/coaching_modes.json`

### 7.4 Prompt Concepts to Master

- **System prompt** — instructions + schema (what the model must output)
- **User prompt** — actual problem + context (what to solve)
- **Few-shot examples** — can be added to prompts for better output
- **Schema prompting** — defining exact JSON keys the LLM must return
- **Mode switching** — same pipeline, different personality via `mode_id`
- **Sanitization** — `sanitize_user_input()` before sending to LLM

---

## 8. Data & Persistence Concepts

### 8.1 Core Entities

| Entity | Purpose |
|--------|---------|
| `AISession` | One analyze/chat session per user |
| `AIMessage` | User and assistant messages per session |
| `ConversationMemory` | Summarized multi-turn context |
| `AgentExecution` | Per-node execution trace |
| `ModelUsage` | Token/cost records |
| `PromptVersion` | DB-stored prompt overrides |
| `LeetCodeProgress` | User practice tracking |

### 8.2 Session Lifecycle

```
PENDING → IN_PROGRESS → COMPLETED
                      → FAILED
                      → MANUAL_REQUIRED (LeetCode URL fetch failed)
```

### 8.3 Conversation Memory

Multi-turn chats use memory:
- `ConversationMemoryService` loads context before LLM call
- `MemoryEngine` + `Summarizer` compress old messages
- `ConversationPruner` limits context size

**Learn:** context window limits, summarization strategies, RAG basics (future).

### 8.4 SQLAlchemy ORM

Standard patterns:
- `Session` from `shared.database.get_db`
- Repository methods: `create_session`, `get_by_id`, `update_session`
- Relationships between sessions and messages

---

## 9. Cross-Cutting Platform Concepts

### 9.1 Configuration

| Source | What |
|--------|------|
| `.env` | API keys, DB URL, OpenRouter settings |
| `shared/config.py` | Shared settings (CORS, Sentry, OpenRouter key) |
| `app/core/config.py` | AI-specific settings (retries, prompt version) |
| `app/config/models.json` | Model catalog |
| `app/config/coaching_modes.json` | Coaching modes |

**Learn:** pydantic-settings, env var precedence, secrets management.

### 9.2 Logging & Monitoring

- Structured logging via `shared.logging.get_logger()`
- Sentry for error tracking (`shared/monitoring/sentry.py`)
- Request ID middleware for tracing

### 9.3 Rate Limiting

- `app/core/rate_limit.py`
- Applied on `/ai/chat` to prevent abuse

### 9.4 Shared Package

`shared/` is imported by all services — never duplicated:
- Database, config, logging, exceptions, middleware, security

**Learn:** monorepo shared library pattern.

---

## 10. LeetCode Agent (Reference Implementation)

Study LeetCode first — it is the complete, working example.

### 10.1 LeetCode-Specific Flow

```
POST /leetcode/analyze
  → LeetCodeService.analyze()
    → LeetCodeProblemFetcher (LeetCode GraphQL API — not OpenRouter)
    → Build ChatRequest(feature=LEETCODE, context=problem, mode_id=...)
    → AIPlatformService.chat()
    → LangGraph pipeline (shared)
    → adapter.to_analyze_response()
    → LeetCodeProgressRepository.record_attempt()
```

### 10.2 LeetCode File Map

| File | Role |
|------|------|
| `agents/leetcode/router.py` | HTTP endpoints |
| `agents/leetcode/service.py` | Thin adapter |
| `agents/leetcode/adapter.py` | Response mapping |
| `agents/leetcode/problem_fetcher.py` | Pre-workflow data fetch |
| `agents/leetcode/schemas.py` | Request/response models |
| `agents/leetcode/agents.py` | Agent declarations |
| `agents/leetcode/catalog.py` | Examples, modes list |
| `prompts/leetcode/v1/single_llm.txt` | LeetCode JSON schema |

### 10.3 Pre-Workflow Pattern

LeetCode fetches problem data **before** the AI pipeline:
- URL validation (`app/utils/leetcode_url.py`)
- GraphQL fetch from leetcode.com
- Fallback to manual input if fetch fails

**Learn:** separating data acquisition from AI reasoning.

---

## 11. Concept Map (How Everything Connects)

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT / GATEWAY                          │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP + JWT
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  main.py → routers (api/ai.py, agents/leetcode/router.py)      │
│  dependencies/services.py → wires everything                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  AIPlatformService (use-case)                                    │
│  - auth check, model resolve, delegate to orchestrator           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  AIPlatformOrchestrator → AIWorkflowEngine (LangGraph)           │
│                                                                  │
│  planner_node ──► openrouter_node ──► teacher_node               │
│       │                  │                  │                    │
│   Planner           OpenRouterClient    TeacherModule            │
│   (rules)           + PromptLoader      (formatter)              │
│                     + ModeRegistry                               │
│                     + JSONValidator                              │
│                          │                                       │
│                          ▼                                       │
│                    OpenRouter API                                │
│                    (the LLM brain)                               │
│                                                                  │
│  ──► coder_node ──► evaluator_node ──► persist_node              │
│       CoderModule    EvaluatorModule    DB + usage + memory      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 12. Learning Path (Step-by-Step)

Follow this order. Spend time on each file before moving on.

### Phase 1 — Foundations (Week 1)

1. Read `docs/architecture.md` — microservice layout
2. Read `app/main.py` — entry point, router mounting
3. Read `app/models/enums.py` — domain vocabulary
4. Read `app/schemas/ai.py` — `ChatRequest`, `ChatResponse`
5. Learn FastAPI basics: routers, Depends, Pydantic models

### Phase 2 — Request Flow (Week 2)

6. Read `app/api/ai.py` — `/ai/chat` handler
7. Read `app/dependencies/services.py` — DI wiring
8. Read `app/services/ai_platform_service.py` — use-case layer
9. Read `app/agents/shared/orchestrator/platform_orchestrator.py`
10. Trace one request mentally: HTTP → service → orchestrator → engine

### Phase 3 — The Pipeline (Week 3)

11. Read `app/agents/shared/workflow/graph.py` — LangGraph setup
12. Read `app/agents/shared/workflow/nodes.py` — all nodes (focus on `openrouter_node`)
13. Read `app/agents/shared/planner/planner.py` — deterministic planning
14. Read `app/agents/shared/teacher/module.py` — formatter pattern
15. Learn LangGraph basics (state graphs, nodes, edges)

### Phase 4 — LLM & Prompts (Week 4)

16. Read `app/clients/openrouter.py` — LLM client
17. Read `app/services/prompt_loader.py` — prompt resolution
18. Read `app/prompts/shared/v1/single_llm.txt` — generic schema
19. Read `app/prompts/leetcode/v1/single_llm.txt` — feature schema
20. Read `app/coaching/registry.py` + `coaching_modes.json`
21. Read `app/schemas/llm_response.py` — `UnifiedLLMResponse`
22. Learn structured output, JSON schema prompting

### Phase 5 — LeetCode End-to-End (Week 5)

23. Read `app/agents/leetcode/router.py`
24. Read `app/agents/leetcode/service.py`
25. Read `app/agents/leetcode/adapter.py`
26. Read `app/agents/leetcode/problem_fetcher.py`
27. Read `app/agents/leetcode/agents.py`
28. Run tests: `pytest services/ai_service/tests/test_leetcode_integration.py -v`

### Phase 6 — Advanced Topics (Week 6+)

29. Follow-up flow: `app/services/followup/followup_service.py`
30. Memory: `app/services/memory/conversation_memory.py`
31. History: `app/services/history/history_manager.py`
32. Usage tracking: `app/services/usage/usage_tracker.py`
33. Gateway proxy: `services/gateway/app/api/ai_proxy.py`
34. Try adding a new coaching mode or calling `/ai/chat` with a new feature

---

## 13. Skills Checklist

Use this to track your learning progress.

### Architecture
- [ ] Explain the 4 layers: HTTP → use-case → orchestration → infrastructure
- [ ] Describe dependency injection in FastAPI
- [ ] Explain repository pattern and why services don't touch SQL directly

### AI Pipeline
- [ ] Draw the LangGraph node sequence from memory
- [ ] Explain why there is only one LLM call in the main workflow
- [ ] Describe what Planner, Teacher, Coder, Evaluator each do
- [ ] Explain the difference between processing modules and product adapters

### LLM Integration
- [ ] Configure OpenRouter API key and model in `.env`
- [ ] Explain structured JSON output and validation retry
- [ ] Describe how system + user prompts are built
- [ ] Explain coaching modes and how `mode_id` affects behavior

### Prompts
- [ ] Find and edit a prompt file under `app/prompts/`
- [ ] Add or modify a coaching mode in `coaching_modes.json`
- [ ] Explain prompt fallback resolution order

### LeetCode Agent
- [ ] Trace `POST /leetcode/analyze` from router to response
- [ ] Explain pre-workflow problem fetching vs AI pipeline
- [ ] Describe the thin adapter pattern with `ChatRequest` / `ChatResponse`

### Building New Features
- [ ] Add a new `AIFeature` enum value
- [ ] Register modules in `_FEATURE_MODULES`
- [ ] Create a feature prompt file
- [ ] Call `/ai/chat` with the new feature (minimal path)
- [ ] Scaffold a product adapter folder like LeetCode (full path)

### Operations
- [ ] Run ai_service locally (Docker or uvicorn)
- [ ] Read execution traces and logs for a failed request
- [ ] Understand rate limiting and auth on endpoints

---

## 14. Glossary

| Term | Meaning |
|------|---------|
| **AIFeature** | Product identifier (`leetcode`, `hackerrank`, `dsa`, etc.) |
| **ChatRequest** | Generic input to the AI platform pipeline |
| **ChatResponse** | Generic output with planner + module results |
| **Coaching mode** | Teaching style config (`learning`, `interview`, `quick`) |
| **ExecutionMode** | How AI runs — only `SINGLE_LLM` exists today |
| **LangGraph** | Library for building state-machine AI workflows |
| **Module** | Pipeline step: planner, teacher, coder, evaluator |
| **ModuleResponse** | Formatted output from one module |
| **OpenRouter** | LLM API gateway used as the model brain |
| **Planner** | Deterministic pre-LLM step — no AI call |
| **Processing module** | Formatter that turns LLM JSON into markdown/cards |
| **Product adapter** | Thin service wrapping the shared platform for one product |
| **PromptLoader** | Loads versioned prompt files from disk or DB |
| **Session** | One user conversation / analyze attempt |
| **single_llm** | Prompt module name for the unified JSON schema |
| **Thin adapter** | Product code that delegates to `AIPlatformService` |
| **UnifiedLLMResponse** | Pydantic model for the one-shot LLM JSON output |
| **WorkflowNodes** | Class containing all LangGraph node implementations |
| **AIWorkflowState** | TypedDict passed between LangGraph nodes |

---

## 15. Key Files Index

Quick reference — open these when working on specific areas.

### Entry & Routing
- `services/ai_service/app/main.py`
- `services/ai_service/app/api/ai.py`
- `services/ai_service/app/agents/leetcode/router.py`

### Wiring & Services
- `services/ai_service/app/dependencies/services.py`
- `services/ai_service/app/services/ai_platform_service.py`

### Workflow & Orchestration
- `services/ai_service/app/agents/shared/orchestrator/platform_orchestrator.py`
- `services/ai_service/app/agents/shared/workflow/graph.py`
- `services/ai_service/app/agents/shared/workflow/nodes.py`

### Agents / Modules
- `services/ai_service/app/agents/shared/planner/planner.py`
- `services/ai_service/app/agents/shared/teacher/module.py`
- `services/ai_service/app/agents/shared/coder/module.py`
- `services/ai_service/app/agents/shared/evaluator/module.py`
- `services/ai_service/app/agents/leetcode/service.py`
- `services/ai_service/app/agents/leetcode/agents.py`

### LLM & Prompts
- `services/ai_service/app/clients/openrouter.py`
- `services/ai_service/app/services/prompt_loader.py`
- `services/ai_service/app/prompts/shared/v1/single_llm.txt`
- `services/ai_service/app/prompts/leetcode/v1/single_llm.txt`
- `services/ai_service/app/coaching/prompts/`
- `services/ai_service/app/config/coaching_modes.json`
- `services/ai_service/app/schemas/llm_response.py`

### Config & Models
- `services/ai_service/app/core/config.py`
- `services/ai_service/app/config/models.json`
- `services/ai_service/app/models/enums.py`

### Tests (learn by reading tests)
- `services/ai_service/tests/test_workflow_engine.py`
- `services/ai_service/tests/test_leetcode_integration.py`
- `services/ai_service/tests/test_ai_platform_service.py`
- `services/ai_service/tests/test_mode_registry.py`

---

## External Resources to Study

These topics are not in the repo but are required background:

| Topic | Why |
|-------|-----|
| [FastAPI docs](https://fastapi.tiangolo.com/) | Routes, Depends, async |
| [Pydantic v2 docs](https://docs.pydantic.dev/) | Schemas, validation |
| [LangGraph docs](https://langchain-ai.github.io/langgraph/) | State graphs, nodes |
| [OpenRouter docs](https://openrouter.ai/docs) | API, models, JSON mode |
| [Prompt engineering guide](https://platform.openai.com/docs/guides/prompt-engineering) | System/user prompts, structured output |
| SQLAlchemy basics | ORM, sessions, repositories |
| JWT authentication | How bearer tokens work |
| Server-Sent Events | Streaming responses |

---

## Summary

To work confidently on the AI service agents, you need to understand:

1. **Layered architecture** — routes, services, orchestrator, modules, clients
2. **Single-LLM pipeline** — one OpenRouter call, then deterministic formatters
3. **LangGraph** — stateful workflow with planner → LLM → teacher → coder → evaluator → persist
4. **Prompt systems** — coaching personality + JSON schema, loaded and composed at runtime
5. **Thin adapter pattern** — product agents prepare context and delegate to the shared platform
6. **Pydantic everywhere** — API contracts, LLM output validation, workflow state
7. **LeetCode as reference** — the complete example to copy when building new products

Start with `main.py`, follow one request through to OpenRouter, then study LeetCode's adapter layer. Everything else builds on those two paths.
