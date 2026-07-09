# Frontend: Dynamic AI Model Selector

Use this prompt in the **recentthink-ai-fe** repo (Cursor / agent) to wire the model dropdown to the backend.

---

## Prompt (copy into frontend agent)

```
Implement a fully dynamic AI Model Selector for the LeetCode chat UI.

## Rules
- NEVER hardcode model IDs, provider names, or OpenRouter secrets in the frontend.
- All model metadata comes from the backend via GET /ai/models (through the gateway).
- Persist per-conversation model choice via PATCH /leetcode/history/{sessionId}.
- The OpenRouter API key stays on the backend only.

## Backend APIs (already implemented)

### List models
GET {NEXT_PUBLIC_GATEWAY_URL}/ai/models
Authorization: Bearer <jwt>

Response:
{
  "default_model": "google/gemini-2.5-flash",
  "models": [
    {
      "id": "google/gemini-2.5-flash",
      "name": "Gemini 2.5 Flash",
      "provider": "Google",
      "description": "Fast, inexpensive and recommended",
      "recommended": true,
      "default": true,
      "enabled": true,
      "tier": "free",
      "context_window": 1000000,
      "supports_vision": true,
      "supports_streaming": true
    }
    // ...more models
  ]
}

### Persist model for active conversation
PATCH {NEXT_PUBLIC_GATEWAY_URL}/leetcode/history/{sessionId}
Authorization: Bearer <jwt>
Body: { "model_id": "deepseek/deepseek-chat" }

### Read session model when opening a chat
GET {NEXT_PUBLIC_GATEWAY_URL}/leetcode/history/{sessionId}
→ response includes `model_id` (nullable)

### New problem analysis (optional model)
POST {NEXT_PUBLIC_GATEWAY_URL}/leetcode/analyze
Body may include: { "model_id": "<selected id>", "problem_url": "..." }

### Follow-up (uses session model automatically)
POST {NEXT_PUBLIC_GATEWAY_URL}/leetcode/follow-up
Body: { "session_id": "...", "question": "..." }
Backend resolves: request.model → session.model_id → default_model

## Implementation tasks

1. **API client**
   - Add `fetchModels(): Promise<ModelsResponse>`
   - Add `updateSessionModel(sessionId: string, modelId: string)`
   - Types matching backend `ModelInfo` (id, name, provider, description, recommended, default, enabled, tier, etc.)

2. **Zustand / state**
   - Replace hardcoded `selectedModelId` defaults with `null` until models load.
   - Store `models: ModelInfo[]`, `defaultModelId: string`, `selectedModelId: string | null`.
   - On app/chat layout mount: call `fetchModels()` once (or React Query with staleTime).

3. **ModelSelector component**
   - Render from `models` array only — no hardcoded list.
   - Show: name, provider, description.
   - Highlight `recommended` models (e.g. star icon).
   - Indicate `default` model in UI.
   - Group or sort: recommended first, then rest.
   - Disabled models should not appear (backend filters them).

4. **When user opens an existing conversation**
   - Load session detail → set `selectedModelId = session.model_id ?? defaultModelId`.

5. **When user changes model in dropdown**
   - Update local `selectedModelId` immediately (optimistic UI).
   - If `sessionId` exists: `PATCH /leetcode/history/{sessionId}` with `{ model_id }`.
   - On PATCH failure: revert selection and show toast.

6. **When user starts a new analyze**
   - Pass `model_id: selectedModelId ?? defaultModelId` in POST /leetcode/analyze body.

7. **Follow-up messages**
   - No need to send model if session was PATCHed; backend uses session.model_id.
   - Optional: still send `model` only if overriding for a single message.

8. **Loading & error states**
   - Skeleton while models load.
   - Fallback message if GET /ai/models fails (do not show hardcoded models).

9. **Security**
   - Never add OPENROUTER_API_KEY to frontend env.
   - Only use NEXT_PUBLIC_GATEWAY_URL.

## Example selector item UI
⭐ Gemini 2.5 Flash
Google · Fast, inexpensive and recommended

DeepSeek V3
DeepSeek · Excellent coding model

## Acceptance criteria
- [ ] Zero hardcoded model IDs in frontend source
- [ ] Dropdown populated from GET /ai/models
- [ ] Changing model PATCHes active session
- [ ] Reopening chat restores model from session.model_id
- [ ] New analyze sends model_id from selector
- [ ] Recommended/default models visually distinct
```

---

## Backend env (for local dev)

Add to `recentthink-ai-be/.env`:

```env
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=google/gemini-2.5-flash
AVAILABLE_MODELS=google/gemini-2.5-flash,deepseek/deepseek-chat,meta-llama/llama-3.3-70b-instruct,openai/gpt-4o,nvidia/llama-3.1-nemotron-ultra-253b-v1
```

Run migration if not applied:

```bash
make migrate
```

---

## Quick API test

```bash
# List models (needs JWT)
curl -s http://localhost:8000/ai/models \
  -H "Authorization: Bearer YOUR_JWT" | jq

# Update session model
curl -s -X PATCH "http://localhost:8000/leetcode/history/SESSION_UUID" \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{"model_id":"openai/gpt-4o"}' | jq
```
