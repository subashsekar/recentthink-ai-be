# AI Workflow Engine

All four AI products share one LangGraph workflow:

```
START → planner → openrouter → teacher → coder → code_explainer → evaluator → persist → END
```

| Node | LLM calls | Role |
|------|-----------|------|
| Planner | 0 | Deterministic module selection |
| OpenRouter | **1** | Single structured JSON completion |
| Teacher / Coder / Code Explainer / Evaluator | 0 | Format-only processors |
| Persist | 0 | Session, memory, usage |

Entry points:

- Platform: `AIPlatformService` / `AIPlatformOrchestrator`
- Graph: `app/agents/shared/workflow/graph.py`
- Thin adapters: `app/agents/{leetcode,hackerrank,dsa_pattern,course_generator}/`

Products never invent a second OpenRouter call for generate/analyze.

## Related

- [AI Service README](../services/ai_service/README.md)
- [Conversation / Streaming](conversation-chat.md)
- [Token / cache notes](../services/ai_service/app/cache/README.md)
- [Completion Report](AI_SERVICE_COMPLETION_REPORT.md)
