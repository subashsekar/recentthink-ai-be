# AI Prompt Builder

Shared prompt composition for all AI products lives in
`services/ai_service/app/prompts/builder/prompt_builder.py`.

## Composition order

1. Shared system prompt  
2. Shared safety prompt  
3. Shared output schema  
4. Feature master prompt (`app/prompts/features/{feature}.md`)  
5. Coaching mode overlay (LeetCode / HackerRank; skipped for DSA / Course)  
6. User / context prompt (problem statement, pattern, course goals, etc.)  
7. Incremental generation rules when `requested_sections` is set  

## Versioning

- Filesystem defaults under `app/prompts/`
- DB overrides via `prompt_versions` + internal admin (`/internal/admin/prompts*`)
- Loader: `app/services/prompt_loader.py`

## Related

- [AI Service README](../services/ai_service/README.md)
- [AI Service Completion Report](AI_SERVICE_COMPLETION_REPORT.md)
- [Conversation / Streaming](conversation-chat.md)
